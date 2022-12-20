"""This module defines functions to interact with the wiki’s database."""
import datetime
import typing as _typ
import urllib.parse

import cssmin
import django.core.handlers.wsgi as dj_wsgi
import django.db.transaction as dj_db_trans
import django.shortcuts as dj_scut
import rjsmin

from . import constants, namespaces
from .. import errors, groups, permissions, utils
from ... import models, requests, settings

MAIN_PAGE_TITLE = namespaces.NS_WIKI.get_full_page_title('Main Page')


def split_title(title: str) -> tuple[namespaces.Namespace, str]:
    """Split the given full page title’s namespace and title.

    :param title: Full page title.
    :return: A tuple containing the page’s namespace and title.
    """
    title = title.strip()
    ns_id = 0
    if namespaces.SEPARATOR in title:
        a, b = title.split(namespaces.SEPARATOR, maxsplit=1)
        if ns := namespaces.NAMESPACE_NAMES.get(a.strip()):
            ns_id = ns.id
            page_title = b.strip()
        else:
            page_title = title
    else:
        page_title = title
    return namespaces.NAMESPACE_IDS[ns_id], page_title


def get_correct_title(raw_title: str) -> str:
    """Return the page title for the given URL-compatible page title.
    Does not check whether the page exists or not.

    :param raw_title: A URL-compatible page title.
    :return: The actual page title.
    """
    return urllib.parse.unquote(raw_title.replace('_', ' ')).strip()


def url_encode_page_title(title: str) -> str:
    """Replace spaces by underscores.

    :param title: Page title to encode.
    :return: The encoded page title.
    """
    return title.replace(' ', '_')


def get_page(ns: namespaces.Namespace, title: str) -> models.Page:
    """Return the page object for the given namespace and title.
    If the page does not exist, a new Page object is returned.

    :param ns: Page’s namespace.
    :param title: Page’s title.
    :return: A Page object.
    """
    try:
        return models.Page.objects.get(namespace_id=ns.id, title=title)
    except models.Page.DoesNotExist:
        return models.Page(
            namespace_id=ns.id,
            title=title,
            content_language=models.Language.get_default(),
        )


def get_js_config(request_params: requests.RequestParams, page: models.Page,
                  special_page_data: dict[str, _typ.Any] = None, revision_id: int = None) -> dict:
    """Return a dict object representing the page’s JS configuration object to insert into the HTML template.

    :param request_params: Request parameters.
    :param page: Page to get the JS configuration of.
    :param special_page_data: Optional special page data.
    :param revision_id: ID of the page’s selected revision.
    :return: The JS object.
    """
    user = request_params.user
    special_page_data = special_page_data or {}
    if page.namespace == namespaces.NS_SPECIAL:
        username = (tu := special_page_data.get('target_user')) and tu.username
    elif page.namespace == namespaces.NS_USER:
        username = page.base_name
    else:
        username = None
    action = request_params.wiki_action
    return {
        'config': {
            'wApiPath': dj_scut.reverse('ottm:wiki_api'),
            'wPath': dj_scut.reverse('ottm:wiki_main_page'),
            'wContentNamespaces': [ns_id for ns_id, ns in namespaces.NAMESPACE_IDS.items() if ns.is_content],
            'wNamespaceNames': {ns_id: ns.name for ns_id, ns in namespaces.NAMESPACE_IDS.items()},
            'wNamespaceIDs': list(namespaces.NAMESPACE_IDS.keys()),
        },
        'page': {
            'wIsMainPage': page.full_title == MAIN_PAGE_TITLE,
            'wAction': action,
            'wID': page.id if page.exists else 0,
            'wNamespaceID': page.namespace.id,
            'wNamespaceName': page.namespace.name,
            'wNamespaceNameURL': url_encode_page_title(page.namespace.name),
            'wTitle': page.title,
            'wTitleURL': url_encode_page_title(page.title),
            'wFullTitle': page.full_title,
            'wFullTitleURL': url_encode_page_title(page.full_title),
            'wBaseName': page.base_name,
            'wBaseNameURL': url_encode_page_title(page.base_name),
            'wName': page.page_name,
            'wNameURL': url_encode_page_title(page.page_name),
            'wCategories': [cat.cat_title for cat in page.get_categories()],
            'wLatestsRevisionID': page.get_latest_revision().id if page.exists else 0,
            'wIsNormalPage': action == constants.ACTION_READ and page.namespace != namespaces.NS_SPECIAL,
            'wIsRedirect': page.redirects_to_namespace_id is not None and page.redirects_to_title is not None,
            'wContentLanguage': page.content_language.code,
            'wContentType': page.content_type,
            'wRedirectedFrom': None,  # TODO
            'wRelevantPage': (tp := special_page_data.get('target_page')) and tp.full_title,
            'wRelevantUser': username,
            'wEditProtection': (pp := page.get_edit_protection()) and pp.protection_level.label,
            'wNamespaceEditProtection': page.namespace.perms_required,
            'wRevisionID': revision_id or 0,
            'wDiffOldID': special_page_data.get('old_id', 0),
            'wDiffNewID': special_page_data.get('new_id', 0),
        },
        'user': {
            'wCanEditPage': page.can_user_edit(user),
            'wCanPostMessages': page.can_user_post_messages(user),
        },
    }


def render_wikicode(code: str, user: models.User, language: settings.UILanguage) -> str:
    """Render the given wikicode.

    :param code: The wikicode to render.
    :param user: The current user.
    :param language: Page’s language.
    :return: The rendered wikicode.
    """
    return code  # TODO


def get_edit_notice(user: models.User, language: settings.UILanguage, page: models.Page) -> str:
    """Return the rendered edit notice from "Interface:EditNotice/<lang_code>".

    :param user: Current user.
    :param language: Page’s language.
    :param page: The page that is requesting the notice.
    :return: The rendered edit notice.
    """
    return get_interface_page(f'EditNotice', user, language, page=page)


def get_new_page_notice(user: models.User, language: settings.UILanguage, page: models.Page) -> str:
    """Return the rendered edit notice from "Interface:NewPageNotice/<lang_code>".

    :param user: Current user.
    :param language: Page’s language.
    :param page: The page that is requesting the notice.
    :return: The rendered new page notice.
    """
    return get_interface_page(f'NewPageNotice', user, language, page=page)


def get_no_page_notice(user: models.User, language: settings.UILanguage) -> str:
    """Return the rendered edit notice from "Interface:NoPageNotice/<lang_code>".

    :param user: Current user.
    :param language: Page’s language.
    :return: The rendered no page notice.
    """
    return get_interface_page('NoPageNotice', user, language)


def get_interface_page(title: str, user: models.User = None, language: settings.UILanguage = None,
                       page: models.Page = None, render: bool = True) -> str:
    """Return the rendered interface page from "Interface:<title>/<lang_code>" if language is defined,
    "Interface:<title>" otherwise.

    :param title: Interface page title.
    :param user: Current user. May be None if render=False.
    :param language: Page’s language. May be None if no localized subpage exists.
    :param page: The page that is requesting the notice.
    :param render: Whether to render the page’s content.
    :return: The rendered notice.
    """
    interface_page = None
    if page:
        for i in range(len(page.title)):  # Check if a notice exists for each variant of the page’s title
            t = f'{title}-{page.namespace_id}-' + (page.title[:-i] if i > 0 else page.title)
            interface_page = _get_interface_page(t, language)
            if interface_page:
                break
        if not interface_page:  # Check if a notice exists for the page’s namespace
            interface_page = _get_interface_page(f'{title}-{page.namespace_id}', language)
    if not interface_page:  # Check if a general notice exists
        interface_page = _get_interface_page(title, language)
    if not interface_page:
        return ''
    return render_wikicode(interface_page.get_content(), user, language) if render else interface_page.get_content()


def _get_interface_page(title: str, language: settings.UILanguage = None) -> models.Page | None:
    """Return the interface page with the given title.

    :param title: Page’s title.
    :param language: If present, '/<language.code>' is appended to the title.
    :return: The page or None if it does not exist.
    """
    if language:
        title += f'/{language.code}'
    try:
        return models.Page.objects.get(namespace_id=namespaces.NS_INTERFACE.id, title=title)
    except models.Page.DoesNotExist:
        return None


@dj_db_trans.atomic
def edit_page(request: dj_wsgi.WSGIRequest | None, author: models.User, page: models.Page, content: str,
              comment: str = None, minor_edit: bool = False, follow: bool = False, hidden_category: bool = False,
              section_id: str = None):
    """Submit a new revision for the given page.
    If the page does not exist, it is created.

    :param request: Client request. May be None for internal calls.
    :param author: Edit’s author.
    :param page: Page to edit.
    :param content: New content of the page.
    :param comment: Edit’s comment.
    :param minor_edit: Whether to mark this revision as minor.
    :param follow: Whether the user wants to follow the page.
    :param hidden_category: Whether the page should be a hidden category.
    :param section_id: ID of the edited page section. Not yet available.
    :raise EditSpecialPageError: If the page is in the "Special" namespace.
    :raise MissingPermissionError: If the user cannot edit the page.
    :raise NotACategoryPageError: If 'hidden_category' is true but the page is not a category.
    :raise ConcurrentWikiEditError: If another edit was made on the same page before this edit.
    :raise ValueError: If the request is None and the user is anonymous.
    """
    if page.namespace == namespaces.NS_SPECIAL:
        raise errors.EditSpecialPageError()
    if not page.can_user_edit(author):
        raise errors.MissingPermissionError(permissions.PERM_WIKI_EDIT)
    if hidden_category and page.namespace != namespaces.NS_CATEGORY:
        raise errors.NotACategoryPageError()
    if False:  # TODO check if another edit was made while editing
        raise errors.ConcurrentWikiEditError()
    if not author.exists:
        if request:
            author.internal_object.save()
        else:
            raise ValueError('missing request')
    if not page.exists or page.get_content() != content:
        if not page.exists:
            # Set content type
            page.content_type = _get_page_content_type(page)
            page.save()
            # Add to log
            models.PageCreationLog(performer=author.internal_object, page=page).save()
        models.PageRevision(
            page=page,
            author=author.internal_object,
            comment=utils.escape_html(comment),
            is_minor=minor_edit,
            content=content,
            is_bot=author.is_bot,
        ).save()
        if page.content_type == constants.CT_JS:
            page.minified_content = minify_js(content)
            page.save()
        elif page.content_type == constants.CT_CSS:
            page.minified_content = minify_css(content)
            page.save()
    if author.is_authenticated:
        follow_page(author, page, follow)


def minify_js(code: str) -> str:  # TODO check syntax and return 'console.log("error")' dummy code
    """Minify the given JavaScript code.

    :param code: JavaScript code to minify.
    :return: The minified code.
    """
    return rjsmin.jsmin(code)


def minify_css(code: str) -> str:  # TODO check syntax and return None if any error
    """Minify the given CSS code.

    :param code: CSS code to minify.
    :return: The minified code.
    """
    return cssmin.cssmin(code)


def _get_page_content_type(page: models.Page) -> str:
    if page.namespace == namespaces.NS_MODULE:
        return constants.CT_MODULE
    # Only pages in namespace Interface and User are allowd to have JS, CSS or JSON pages.
    # For User namespace, only subpages can have either of these types, user page itself cannot.
    if page.namespace == namespaces.NS_INTERFACE or page.namespace == namespaces.NS_USER and '/' in page.title:
        if page.title.endswith('.js'):
            return constants.CT_JS
        if page.title.endswith('.css'):
            return constants.CT_CSS
        if page.title.endswith('.json'):
            return constants.CT_JSON
    return constants.CT_WIKIPAGE


@dj_db_trans.atomic
def set_page_content_language(author: models.User, page: models.Page, language: settings.UILanguage, reason: str):
    """Change the content language of the given page.

    :param author: User performing the action.
    :param page: Page to alter.
    :param language: New content language.
    :param reason: Reason for the change.
    :return: True if the action succeeded, false otherwise.
    :raise PageDoesNotExistError: If the page does not exist.
    :raise EditSpecialPageError: If the page is in the "Special" namespace.
    :raise MissingPermissionError: If the user cannot edit the page.
    """
    if not page.exists:
        raise errors.PageDoesNotExistError(page.full_title)
    if page.namespace == namespaces.NS_SPECIAL:
        raise errors.EditSpecialPageError()
    if not page.can_user_edit(author):
        raise errors.MissingPermissionError(permissions.PERM_WIKI_EDIT)
    if not author.exists:
        author.internal_object.save()
    if language.internal_language == page.content_language:
        return False
    page.content_language = language.internal_language
    page.save()
    models.PageContentLanguageLog(
        performer=author.internal_object,
        page=page,
        language=page.content_language,
        reason=reason,
    ).save()
    return True


@dj_db_trans.atomic
def set_page_content_type(author: models.User, page: models.Page, content_type: str, reason: str):
    """Change the content type of the given page.

    :param author: User performing the action.
    :param page: Page to alter.
    :param content_type: New content type.
    :param reason: Reason for the change.
    :return: True if the action succeeded, false otherwise.
    :raise PageDoesNotExistError: If the page does not exist.
    :raise EditSpecialPageError: If the page is in the "Special" namespace.
    :raise MissingPermissionError: If the user cannot edit the page.
    """
    if not page.exists:
        raise errors.PageDoesNotExistError(page.full_title)
    if page.namespace == namespaces.NS_SPECIAL:
        raise errors.EditSpecialPageError()
    if not page.can_user_edit(author):
        raise errors.MissingPermissionError(permissions.PERM_WIKI_EDIT)
    if not author.exists:
        author.internal_object.save()
    if content_type == page.content_type:
        return False
    page.content_type = content_type
    page.save()
    models.PageContentTypeLog(
        performer=author.internal_object,
        page=page,
        content_type=content_type,
        reason=reason,
    ).save()
    return True


@dj_db_trans.atomic
def follow_page(user: models.User, page: models.Page, follow: bool, until: datetime.datetime = None):
    """Make a user follow/unfollow the given page.

    :param user: The user.
    :param page: The page to add/remove to the user’s follow list.
    :param follow: Whether to add or remove the page from the user’s follow list.
    :param until: Date after which the follow status will be removed.
    :return: True if the operation was successful, false otherwise.
    :raise AnonymousFollowPageError: If the user is not logged in.
    :raise FollowSpecialPageError: If the page is in the "Special" namespace.
    """
    if not user.is_authenticated:
        raise errors.AnonymousFollowPageError()
    if page.namespace == namespaces.NS_SPECIAL:
        raise errors.FollowSpecialPageError()

    def delete_follow():
        try:
            user.internal_object.followed_pages.get(
                page_namespace_id=page.namespace_id,
                page_title=page.title,
            ).delete()
        except models.PageFollowStatus.DoesNotExist:
            pass

    if follow:
        delete_follow()
        models.PageFollowStatus(
            user=user.internal_object,
            page_namespace_id=page.namespace_id,
            page_title=page.title,
            end_date=until,
        ).save()
    elif not follow:
        delete_follow()


@dj_db_trans.atomic
def protect_page(author: models.User, page: models.Page, protection_level: models.UserGroup, protect_talks: bool,
                 reason: str = None, until: datetime.datetime = None) -> bool:
    f"""Change the protection status of the given page.
    If a the page is already protected, the status will be replaced by the new one.

    :param author: User performing the action.
    :param page: The page.
    :param protection_level: The new protection level. If the new level is {groups.GROUP_ALL},
        any pre-existing protection will be removed.
    :param protect_talks: Whether to also protect talks.
    :param reason: The reason behind the new protection status.
    :param until: The date until which the page will be protected. If None, the protection will never end.
    :return: True if the operation succeeded, false otherwise.
    :raise MissingPermissionError: If the user does not have the {permissions.PERM_WIKI_PROTECT} permission.
    :raise ProtectSpecialPageError: If the page is in the "Special" namespace.
    :raise PastDateError: If the date is in the past.
    """
    if not author.has_permission(permissions.PERM_WIKI_PROTECT):
        raise errors.MissingPermissionError(permissions.PERM_WIKI_PROTECT)
    if page.namespace == namespaces.NS_SPECIAL:
        raise errors.ProtectSpecialPageError()
    if until and until <= utils.now().date():
        raise errors.PastDateError()
    try:
        pp = models.PageProtection.objects.get(page_namespace_id=page.namespace_id, page_title=page.title)
    except models.PageProtection.DoesNotExist:
        if protection_level.label == groups.GROUP_ALL:
            return False
    else:
        if pp.protection_level == protection_level and pp.end_date == until and pp.protect_talks == protect_talks:
            return False
        pp.delete()
    reason = utils.escape_html(reason)
    protect = protection_level.label != groups.GROUP_ALL
    end_date = until if protect else None
    if protect:
        models.PageProtection(
            page_namespace_id=page.namespace_id,
            page_title=page.title,
            end_date=end_date,
            reason=reason,
            protect_talks=protect_talks,
            protection_level=protection_level,
        ).save()
    models.PageProtectionLog(
        performer=author.internal_object,
        page=page,
        end_date=end_date,
        reason=reason,
        protect_talks=protect_talks,
        protection_level=protection_level,
    ).save()
    return True


def get_page_protection_log_entry(page: models.Page) -> models.PageProtectionLog | None:
    """Return the latest page protection log entry for the given page.

    :param page: The page.
    :return: The log entry or None if there is none.
    """
    try:
        pp = models.PageProtection.objects.get(page_namespace_id=page.namespace_id, page_title=page.title)
    except models.PageProtection.DoesNotExist:
        return None
    if not pp.is_active:
        return None
    try:
        return models.PageProtectionLog.objects.filter(page=page).latest()
    except models.PageProtectionLog.DoesNotExist:
        return None
