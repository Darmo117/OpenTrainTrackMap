"""This module defines functions to interact with the wiki’s database."""
import datetime
import urllib.parse

import django.core.handlers.wsgi as dj_wsgi
import django.db.transaction as dj_db_trans

from . import constants, namespaces
from .. import auth, errors, groups, permissions, utils
from ... import models, settings

MAIN_PAGE_TITLE = namespaces.NS_WIKI.get_full_page_title('Main Page')


def split_title(title: str) -> tuple[namespaces.Namespace, str]:
    """Split the given full page title’s namespace and title.

    :param title: Full page title.
    :return: A tuple containing the page’s namespace and title.
    """
    ns_id = 0
    if namespaces.SEPARATOR in title:
        a, b = title.split(namespaces.SEPARATOR, maxsplit=1)
        if ns := namespaces.NAMESPACE_NAMES.get(a):
            ns_id = ns.id
            page_title = b
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
    return urllib.parse.unquote(raw_title.replace('_', ' '))


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


def get_js_config(page: models.Page, action: str) -> dict:
    """Return a dict object representing the page’s JS configuration object to insert into the HTML template.

    :param page: Page to get the JS configuration of.
    :param action: Page’s action.
    :return: The JS object.
    """
    return {
        'pageNamespaceID': page.namespace.id,
        'pageNamespaceName': page.namespace.name,
        'pageTitle': page.title,
        'action': action,
        # TODO
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
    if request:
        if author.is_anonymous:
            author = auth.get_or_create_anonymous_account_from_request(request)
        else:
            raise ValueError('missing request')
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
    if author.is_authenticated:
        follow_page(author, page, follow)


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
def set_page_content_language(request: dj_wsgi.WSGIRequest, author: models.User, page: models.Page,
                              language: settings.UILanguage, reason: str):
    """Change the content language of the given page.

    :param request: Client request.
    :param author: User performing the action.
    :param page: Page to alter.
    :param language: New content language.
    :param reason: Reason for the change.
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
    if author.is_anonymous:
        author = auth.get_or_create_anonymous_account_from_request(request)
    page.content_language = language.internal_language
    page.save()
    models.PageContentLanguageLog(
        performer=author.internal_object,
        page=page,
        language=page.content_language,
        reason=reason,
    ).save()


@dj_db_trans.atomic
def set_page_content_type(request: dj_wsgi.WSGIRequest, author: models.User, page: models.Page,
                          content_type: str, reason: str):
    """Change the content type of the given page.

    :param request: Client request.
    :param author: User performing the action.
    :param page: Page to alter.
    :param content_type: New content type.
    :param reason: Reason for the change.
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
    if author.is_anonymous:
        author = auth.get_or_create_anonymous_account_from_request(request)
    page.content_type = content_type
    page.save()
    models.PageContentTypeLog(
        performer=author.internal_object,
        page=page,
        content_type=content_type,
        reason=reason,
    ).save()


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
    if user.is_anonymous or not user.is_authenticated:
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
def protect_page(author: models.User, page: models.Page, protection_level: models.UserGroup, reason: str = None,
                 until: datetime.datetime = None):
    f"""Change the protection status of the given page.
    If a the page is already protected, the status will be replaced by the new one.

    :param author: User performing the action.
    :param page: The page.
    :param protection_level: The new protection level. If the new level is {groups.GROUP_ALL},
        any pre-existing protection will be removed.
    :param reason: The reason behind the new protection status.
    :param until: The date until which the page will be protected. If None, the protection will never end.
    :raise MissingPermissionError: If the user does not have the {permissions.PERM_WIKI_PROTECT} permission.
    :raise ProtectSpecialPageError: If the page is in the "Special" namespace.
    """
    if not author.has_permission(permissions.PERM_WIKI_PROTECT):
        raise errors.MissingPermissionError(permissions.PERM_WIKI_PROTECT)
    if page.namespace == namespaces.NS_SPECIAL:
        raise errors.ProtectSpecialPageError()
    try:
        pp = models.PageProtection.objects.get(page_namespace_id=page.namespace_id, page_title=page.title)
    except models.PageProtection.DoesNotExist:
        pass
    else:
        pp.delete()
    reason = utils.escape_html(reason)
    if protection_level.label != groups.GROUP_ALL:
        models.PageProtection(
            page_namespace_id=page.namespace_id,
            page_title=page.title,
            end_date=until,
            reason=reason,
            protection_level=protection_level,
        ).save()
    models.PageProtectionLog(
        performer=author.internal_object,
        page=page,
        end_date=until,
        reason=reason,
        protection_level=protection_level,
    ).save()


def get_page_protection_log_entry(page: models.Page) -> models.PageProtectionLog | None:
    """Return the latest page protection log entry for the given page.

    :param page: The page.
    :return: The log entry or None if there is none.
    """
    try:
        pp = models.PageProtection.objects.get(page_namespace_id=page.namespace_id, page_title=page.title)
    except models.PageProtection.DoesNotExist:
        return None
    if pp.end_date and pp.end_date >= utils.now():
        return None
    try:
        return models.PageProtectionLog.objects.filter(page=page).latest()
    except models.PageProtectionLog.DoesNotExist:
        return None
