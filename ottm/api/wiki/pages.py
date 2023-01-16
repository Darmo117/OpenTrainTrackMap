"""This module defines functions to interact with the wiki’s database."""
import datetime as _dt
import typing as _typ
import urllib.parse as _url_parse

import cssmin as _cssmin
import django.db.transaction as _dj_db_trans
import django.shortcuts as _dj_scut
import rjsmin as _rjsmin

from . import constants as _w_cons, namespaces as _w_ns, parser as _parser
from .. import errors as _errors, groups as _groups, permissions as _perms, utils as _utils
from ... import models as _models, requests as _requests, settings as _settings

MAIN_PAGE_TITLE = _w_ns.NS_WIKI.get_full_page_title('Main Page')


def split_title(title: str) -> tuple[_w_ns.Namespace, str]:
    """Split the given full page title’s namespace and title.

    :param title: Full page title.
    :return: A tuple containing the page’s namespace and title.
    """
    title = title.strip()
    ns_id = 0
    if _w_ns.SEPARATOR in title:
        a, b = title.split(_w_ns.SEPARATOR, maxsplit=1)
        if ns := _w_ns.NAMESPACE_NAMES.get(a.strip()):
            ns_id = ns.id
            page_title = b.strip()
        else:
            page_title = title
    else:
        page_title = title
    return _w_ns.NAMESPACE_IDS[ns_id], page_title


def get_correct_title(raw_title: str) -> str:
    """Return the page title for the given URL-compatible page title.
    Does not check whether the page exists or not.

    :param raw_title: A URL-compatible page title.
    :return: The actual page title.
    """
    return _url_parse.unquote(raw_title.replace('_', ' ')).strip()


def url_encode_page_title(title: str) -> str:
    """Replace spaces by underscores.

    :param title: Page title to encode.
    :return: The encoded page title.
    """
    return title.replace(' ', '_')


def get_page(ns: _w_ns.Namespace, title: str) -> _models.Page:
    """Return the page object for the given namespace and title.
    If the page does not exist, a new Page object is returned.

    `Does not check if the title is valid.`

    :param ns: Page’s namespace.
    :param title: Page’s title.
    :return: A Page object.
    """
    try:
        return _models.Page.objects.get(namespace_id=ns.id, title=title)
    except _models.Page.DoesNotExist:
        return _models.Page(
            namespace_id=ns.id,
            title=title,
            content_language=_models.Language.get_default(),
        )


def get_js_config(request_params: _requests.RequestParams, page: _models.Page,
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
    if page.namespace == _w_ns.NS_SPECIAL:
        username = (tu := special_page_data.get('target_user')) and tu.username
    elif page.namespace == _w_ns.NS_USER:
        username = page.base_name
    else:
        username = None
    action = request_params.wiki_action
    return {
        'config': {
            'wApiPath': _dj_scut.reverse('ottm:wiki_api'),
            'wPath': _dj_scut.reverse('ottm:wiki_main_page'),
            'wContentNamespaces': [ns_id for ns_id, ns in _w_ns.NAMESPACE_IDS.items() if ns.is_content],
            'wNamespaceNames': {ns_id: ns.name for ns_id, ns in _w_ns.NAMESPACE_IDS.items()},
            'wNamespaceIDs': list(_w_ns.NAMESPACE_IDS.keys()),
        },
        'page': {
            'wIsMainPage': page.full_title == MAIN_PAGE_TITLE,
            'wAction': action,
            'wID': page.id if page.exists and page.namespace != _w_ns.NS_SPECIAL else 0,
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
            'wLatestsRevisionID':
                page.get_latest_revision().id if page.exists and page.namespace != _w_ns.NS_SPECIAL else 0,
            'wIsNormalPage': action == _w_cons.ACTION_READ and page.namespace != _w_ns.NS_SPECIAL,
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


def render_wikicode(code: str, page: _models.Page, revision: _models.PageRevision) \
        -> tuple[str, _parser.ParsingMetadata]:
    """Render the given wikicode.

    :param code: The wikicode to render.
    :param page: The current page.
    :param revision: The page revision to render.
    :return: The rendered wikicode and the associated parser metadata.
    """
    parser = _parser.Parser(page, revision)
    parsed = parser.parse(code)
    return parsed, parser.output_metadata


def get_edit_notice(language: _settings.UILanguage, page: _models.Page) -> str:
    """Return the rendered edit notice from "Interface:EditNotice/<lang_code>".

    :param language: Page’s language.
    :param page: The page that is requesting the notice.
    :return: The rendered edit notice.
    """
    return get_interface_page(f'EditNotice', language, page=page)


def get_new_page_notice(language: _settings.UILanguage, page: _models.Page) -> str:
    """Return the rendered edit notice from "Interface:NewPageNotice/<lang_code>".

    :param language: Page’s language.
    :param page: The page that is requesting the notice.
    :return: The rendered new page notice.
    """
    return get_interface_page(f'NewPageNotice', language, page=page)


def get_no_page_notice(language: _settings.UILanguage) -> str:
    """Return the rendered edit notice from "Interface:NoPageNotice/<lang_code>".

    :param language: Page’s language.
    :return: The rendered no page notice.
    """
    return get_interface_page('NoPageNotice', language)


def get_interface_page(title: str, language: _settings.UILanguage = None,
                       page: _models.Page = None, rendered: bool = True) -> str:
    """Return the rendered interface page from "Interface:<title>/<lang_code>" if language is defined,
    "Interface:<title>" otherwise.

    :param title: Interface page title.
    :param language: Page’s language. May be None if no localized subpage exists.
    :param page: The page that is requesting the notice.
    :param rendered: True to return the cached rendered page content, false to return the wikicode.
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
    if rendered:
        return interface_page.cached_parsed_content
    return interface_page.get_content()


def _get_interface_page(title: str, language: _settings.UILanguage = None) -> _models.Page | None:
    """Return the interface page with the given title.

    :param title: Page’s title.
    :param language: If present, '/<language.code>' is appended to the title.
    :return: The page or None if it does not exist.
    """
    if language:
        title += f'/{language.code}'
    try:
        return _models.Page.objects.get(namespace_id=_w_ns.NS_INTERFACE.id, title=title)
    except _models.Page.DoesNotExist:
        return None


# noinspection PyUnreachableCode
@_dj_db_trans.atomic
def edit_page(author: _models.User, page: _models.Page, content: str, comment: str = None, minor_edit: bool = False,
              follow: bool = False, hidden_category: bool = False, section_id: str = None):
    """Submit a new revision for the given page.
    If the page does not exist, it is created.

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
    if page.namespace == _w_ns.NS_SPECIAL:
        raise _errors.EditSpecialPageError()
    if not page.can_user_edit(author):
        raise _errors.MissingPermissionError(_perms.PERM_WIKI_EDIT)
    if hidden_category and page.namespace != _w_ns.NS_CATEGORY:
        raise _errors.NotACategoryPageError()
    if False:  # TODO check if another edit was made while editing
        raise _errors.ConcurrentWikiEditError()
    if not author.exists:
        author.internal_object.save()
    if not page.exists or page.get_content() != content:
        creation = not page.exists
        if creation:
            if page.deleted:
                page.deleted = False
            page.content_type = _get_page_content_type(page)
            page.save()
            _models.PageCreationLog(performer=author.internal_object, page=page).save()
        revision = _models.PageRevision(
            page=page,
            author=author.internal_object,
            comment=_utils.escape_html(comment),
            is_minor=minor_edit,
            content=content,
            is_bot=author.is_bot,
            page_creation=creation,
        )
        revision.save()
    else:
        revision = page.get_latest_revision()
    # All pages are parsed to at least detect categories and linked pages
    # Actual parsed content is only used for pages other than JS, JSON, CSS and modules.
    parsed_content, parse_metadata = render_wikicode(content, page, revision)
    if page.content_type == _w_cons.CT_JS:
        page.cached_parsed_content = minify_js(content)
    elif page.content_type == _w_cons.CT_CSS:
        page.cached_parsed_content = minify_css(content)
    elif page.content_type == _w_cons.CT_JSON:
        page.cached_parsed_content = minify_js(content)
    elif page.content_type == _w_cons.CT_MODULE:
        page.cached_parsed_content = content
    elif page.content_type == _w_cons.CT_WIKIPAGE:
        page.cached_parsed_content = parsed_content
    page.parse_time = parse_metadata.parse_duration
    page.parse_date = parse_metadata.parse_date
    page.size_before_parse = parse_metadata.size_before
    page.size_after_parse = parse_metadata.size_after
    page.cached_parsed_revision_id = revision.id
    page.cache_expiry_date = parse_metadata.parse_date + _dt.timedelta(seconds=_settings.WIKI_PAGE_CACHE_TTL)
    # Update linked pages
    for page_link_metadata in page.embedded_links.all():
        page_link_metadata.delete()
    for ns_id, title in parse_metadata.links:
        _models.PageLink(page=page, page_namespace_id=ns_id, page_title=title).save()
    # Update categories
    for page_category in page.categories.all():
        page_category.delete()
    for category_name, sort_key in parse_metadata.categories:
        _models.PageCategory(page=page, cat_title=category_name, sort_key=sort_key).save()
    page.save()
    if author.is_authenticated:
        follow_page(author, page, follow)


def minify_js(code: str) -> str:  # TODO check syntax and return 'console.log("error")' dummy code
    """Minify the given JavaScript code.

    :param code: JavaScript code to minify.
    :return: The minified code.
    """
    return _rjsmin.jsmin(code)


def minify_css(code: str) -> str:  # TODO check syntax and return None if any error
    """Minify the given CSS code.

    :param code: CSS code to minify.
    :return: The minified code.
    """
    return _cssmin.cssmin(code)


def _get_page_content_type(page: _models.Page) -> str:
    if page.namespace == _w_ns.NS_MODULE:
        return _w_cons.CT_MODULE
    # Only pages in namespace Interface and User are allowd to have JS, CSS or JSON pages.
    # For User namespace, only subpages can have either of these types, user page itself cannot.
    if page.namespace == _w_ns.NS_INTERFACE or page.namespace == _w_ns.NS_USER and '/' in page.title:
        if page.title.endswith('.js'):
            return _w_cons.CT_JS
        if page.title.endswith('.css'):
            return _w_cons.CT_CSS
        if page.title.endswith('.json'):
            return _w_cons.CT_JSON
    return _w_cons.CT_WIKIPAGE


@_dj_db_trans.atomic
def set_page_content_language(performer: _models.User, page: _models.Page, language: _settings.UILanguage, reason: str):
    """Change the content language of the given page.

    :param performer: User performing the action.
    :param page: Page to alter.
    :param language: New content language.
    :param reason: Reason for the change.
    :return: True if the action succeeded, false otherwise.
    :raise PageDoesNotExistError: If the page does not exist.
    :raise EditSpecialPageError: If the page is in the "Special" namespace.
    :raise CannotEditPageError: If the user cannot edit the page.
    """
    if not page.exists:
        raise _errors.PageDoesNotExistError(page.full_title)
    if page.namespace == _w_ns.NS_SPECIAL:
        raise _errors.EditSpecialPageError()
    if not page.can_user_edit(performer):
        raise _errors.CannotEditPageError(page.full_title)
    if not performer.exists:
        performer.internal_object.save()
    if language.internal_language == page.content_language:
        return False
    page.content_language = language.internal_language
    page.save()
    _models.PageContentLanguageLog(
        performer=performer.internal_object,
        page=page,
        language=page.content_language,
        reason=reason,
    ).save()
    return True


@_dj_db_trans.atomic
def set_page_content_type(performer: _models.User, page: _models.Page, content_type: str, reason: str):
    """Change the content type of the given page.

    :param performer: User performing the action.
    :param page: Page to alter.
    :param content_type: New content type.
    :param reason: Reason for the change.
    :return: True if the action succeeded, false otherwise.
    :raise PageDoesNotExistError: If the page does not exist.
    :raise EditSpecialPageError: If the page is in the "Special" namespace.
    :raise CannotEditPageError: If the user cannot edit the page.
    """
    if not page.exists:
        raise _errors.PageDoesNotExistError(page.full_title)
    if page.namespace == _w_ns.NS_SPECIAL:
        raise _errors.EditSpecialPageError()
    if not page.can_user_edit(performer):
        raise _errors.CannotEditPageError(page.full_title)
    if not performer.exists:
        performer.internal_object.save()
    if content_type == page.content_type:
        return False
    page.content_type = content_type
    page.save()
    _models.PageContentTypeLog(
        performer=performer.internal_object,
        page=page,
        content_type=content_type,
        reason=reason,
    ).save()
    return True


@_dj_db_trans.atomic
def update_follow_list(user: _models.User, *pages: _models.Page):
    """Update the given user’s follow list.

    :param user: The user.
    :param pages: The list of pages.
    :raise AnonymousFollowPageError: If the user is not logged in.
    :raise FollowSpecialPageError: If one of the pages is in the "Special" namespace.
    """
    followed_pages = user.get_followed_pages()
    for page in followed_pages:
        if page not in pages:
            unfollow_page(user, page)
    for page in pages:
        if page not in followed_pages:
            follow_page(user, page, follow=True)


@_dj_db_trans.atomic
def follow_page(user: _models.User, page: _models.Page, follow: bool, until: _dt.datetime = None):
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
        raise _errors.AnonymousFollowPageError()
    if page.namespace == _w_ns.NS_SPECIAL:
        raise _errors.FollowSpecialPageError()

    if follow:
        unfollow_page(user, page)
        _models.PageFollowStatus(
            user=user.internal_object,
            page_namespace_id=page.namespace_id,
            page_title=page.title,
            end_date=until,
        ).save()
    elif not follow:
        unfollow_page(user, page)


@_dj_db_trans.atomic
def unfollow_page(user: _models.User, page: _models.Page):
    """Make a user unfollow a specific page.

    :param user: The user.
    :param page: The page to unfollow.
    """
    if not user.is_authenticated:
        return
    try:
        user.internal_object.followed_pages.get(
            page_namespace_id=page.namespace_id,
            page_title=page.title,
        ).delete()
    except _models.PageFollowStatus.DoesNotExist:
        pass


@_dj_db_trans.atomic
def clear_follow_list(user: _models.User):
    """Clear the follow list of the specified user.

    :param user: The user.
    """
    if not user.is_authenticated:
        return
    for pfs in user.internal_object.followed_pages.all():
        try:
            pfs.delete()
        except _models.PageFollowStatus.DoesNotExist:
            pass


@_dj_db_trans.atomic
def protect_page(performer: _models.User, page: _models.Page, protection_level: _models.UserGroup, protect_talks: bool,
                 reason: str = None, until: _dt.datetime = None) -> bool:
    f"""Change the protection status of the given page.
    If a the page is already protected, the status will be replaced by the new one.

    :param performer: User performing the action.
    :param page: The page.
    :param protection_level: The new protection level. If the new level is {_groups.GROUP_ALL},
        any pre-existing protection will be removed.
    :param protect_talks: Whether to also protect talks.
    :param reason: The reason behind the new protection status.
    :param until: The date until which the page will be protected. If None, the protection will never end.
    :return: True if the operation succeeded, false otherwise.
    :raise MissingPermissionError: If the user does not have the {_perms.PERM_WIKI_PROTECT} permission.
    :raise CannotEditPageError: If the user cannot edit the page.
    :raise ProtectSpecialPageError: If the page is in the "Special" namespace.
    :raise PastDateError: If the date is in the past.
    """
    if not performer.has_permission(_perms.PERM_WIKI_PROTECT):
        raise _errors.MissingPermissionError(_perms.PERM_WIKI_PROTECT)
    if page.namespace == _w_ns.NS_SPECIAL:
        raise _errors.ProtectSpecialPageError()
    if not page.can_user_edit(performer):
        raise _errors.CannotEditPageError(page.full_title)
    if until and until <= _utils.now().date():
        raise _errors.PastDateError()
    if not performer.exists:
        performer.internal_object.save()
    try:
        pp = _models.PageProtection.objects.get(page_namespace_id=page.namespace_id, page_title=page.title)
    except _models.PageProtection.DoesNotExist:
        if protection_level.label == _groups.GROUP_ALL:
            return False
    else:
        if pp.protection_level == protection_level and pp.end_date == until and pp.protect_talks == protect_talks:
            return False
        pp.delete()
    reason = _utils.escape_html(reason)
    protect = protection_level.label != _groups.GROUP_ALL
    end_date = until if protect else None
    if protect:
        _models.PageProtection(
            page_namespace_id=page.namespace_id,
            page_title=page.title,
            end_date=end_date,
            reason=reason,
            protect_talks=protect_talks,
            protection_level=protection_level,
        ).save()
    _models.PageProtectionLog(
        performer=performer.internal_object,
        page_namespace_id=page.namespace_id,
        page_title=page.title,
        end_date=end_date,
        reason=reason,
        protect_talks=protect_talks,
        protection_level=protection_level,
    ).save()
    return True


@_dj_db_trans.atomic
def delete_page(performer: _models.User, page: _models.Page, reason: str = None):
    f"""Delete a page.

    :param performer: The user performing the action.
    :param page: The page to delete.
    :param reason: The deletion reason.
    :raise PageDoesNotExistError: If the page does not exist.
    :raise MissingPermissionError: If the user does not have the {_perms.PERM_WIKI_DELETE} permission.
    :raise CannotEditPageError: If the user cannot edit the page.
    :raise DeleteSpecialPageError: If the page is in the "Special" namespace.
    """
    if not page.exists:
        raise _errors.PageDoesNotExistError(page.full_title)
    if not performer.has_permission(_perms.PERM_WIKI_DELETE):
        raise _errors.MissingPermissionError(_perms.PERM_WIKI_DELETE)
    if page.namespace == _w_ns.NS_SPECIAL:
        raise _errors.DeleteSpecialPageError()
    if not page.can_user_edit(performer):
        raise _errors.CannotEditPageError(page.full_title)
    if not performer.exists:
        performer.internal_object.save()
    page.deleted = True
    page.save()
    _models.PageDeletionLog(
        page=page,
        performer=performer.internal_object,
        reason=reason,
    ).save()


@_dj_db_trans.atomic
def rename_page(performer: _models.User, page: _models.Page, new_title: str, leave_redirect: bool, reason: str = None):
    f"""Rename a page.

    :param performer: The user performing the action.
    :param page: The page to rename.
    :param new_title: Page’s new title.
    :param leave_redirect: Whether to leave a redirect to the new title.
    :param reason: The reason for renaming.
    :raise PageDoesNotExistError: If the page does not exist.
    :raise TitleAlreadyExistsError: If the target title already exists.
    :raise MissingPermissionError: If the user does not have the {_perms.PERM_WIKI_RENAME} permission.
    :raise CannotEditPageError: If the user cannot edit the old page or the new page.
    :raise RenameSpecialPageError: If the page is in the "Special" namespace.
    """
    if not page.exists:
        raise _errors.PageDoesNotExistError(page.full_title)
    new_page = get_page(*split_title(new_title))
    if new_page.exists:
        raise _errors.TitleAlreadyExistsError(page.full_title)
    if not performer.has_permission(_perms.PERM_WIKI_RENAME):
        raise _errors.MissingPermissionError(_perms.PERM_WIKI_RENAME)
    if page.namespace == _w_ns.NS_SPECIAL:
        raise _errors.RenameSpecialPageError()
    if not page.can_user_edit(performer):
        raise _errors.CannotEditPageError(page.full_title)
    if not new_page.can_user_edit(performer):
        raise _errors.CannotEditPageError(new_page.full_title)
    if not performer.exists:
        performer.internal_object.save()
    old_name = page.full_title
    old_ns_id = page.namespace_id
    old_title = page.title
    page.namespace_id = new_page.namespace_id
    page.title = new_page.title
    page.save()
    if leave_redirect or not performer.has_permission(_perms.PERM_WIKI_DELETE):
        edit_page(performer, get_page(_w_ns.NAMESPACE_IDS[old_ns_id], old_title),
                  _parser.Parser.get_redirect_link(new_title),
                  comment=reason, follow=page.is_user_following(performer))
    _models.PageRenameLog(
        page=page,
        performer=performer.internal_object,
        old_title=old_name,
        new_title=new_title,
        leave_redirect=leave_redirect,
        reason=reason,
    ).save()


@_dj_db_trans.atomic
def change_revisions_visibility(performer: _models.User, revision_ids: list[int], action: str, reason: str = None):
    f"""Change the visibility of a list of page revisions.

    :param performer: User performing the action.
    :param revision_ids: List of revision IDs to change the visibility of.
    :param action: Action to perform on all revision IDs.
    :param reason: Reason for the visibility change.
    :raise MissingPermissionError: If the user does not have the {_perms.PERM_MASK} permission.
    :raise CannotEditPageError: If the user cannot edit one of the revisions’ page.
    :raise PageRevisionDoesNotExistError: If one of the revision IDs does not exist.
    :raise CannotMaskLastRevisionError: If one of the revision IDs is the last visible of its page.
    :raise NoRevisionsError: If no revision ID is provided.
    """
    if not performer.has_permission(_perms.PERM_WIKI_RENAME):
        raise _errors.MissingPermissionError(_perms.PERM_WIKI_RENAME)
    if not revision_ids:
        raise _errors.NoRevisionsError()
    if not performer.exists:
        performer.internal_object.save()

    for revid in revision_ids:
        try:
            revision = _models.PageRevision.objects.get(id=revid)
        except _models.PageRevision.DoesNotExist:
            raise _errors.PageRevisionDoesNotExistError(revid)
        page = revision.page
        if not page.can_user_edit(performer):
            raise _errors.CannotEditPageError(page.full_title)
        if not revision.get_next(ignore_hidden=True):
            raise _errors.CannotMaskLastRevisionError(revid)

        match action:
            case _models.PageRevisionMaskLog.MASK_FULLY:
                revision.hidden = True
                revision.comment_hidden = True
            case _models.PageRevisionMaskLog.MASK_COMMENTS_ONLY:
                revision.comment_hidden = True
            case _models.PageRevisionMaskLog.UNMASK_ALL:
                revision.hidden = False
                revision.comment_hidden = False
            case _models.PageRevisionMaskLog.UNMASK_ALL_BUT_COMMENTS:
                revision.hidden = False
            case _:
                raise ValueError(f'invalid action {action!r}')
        revision.save()
        _models.PageRevisionMaskLog(
            performer=performer.internal_object,
            revision=revision,
            action=action,
            reason=reason,
        ).save()


def get_page_protection_log_entry(page: _models.Page) -> _models.PageProtectionLog | None:
    """Return the latest page protection log entry for the given page.

    :param page: The page.
    :return: The log entry or None if there is none.
    """
    try:
        pp = _models.PageProtection.objects.get(page_namespace_id=page.namespace_id, page_title=page.title)
    except _models.PageProtection.DoesNotExist:
        return None
    if not pp.is_active:
        return None
    try:
        return _models.PageProtectionLog.objects.filter(page_namespace_id=page.namespace_id,
                                                        page_title=page.title).latest()
    except _models.PageProtectionLog.DoesNotExist:
        return None
