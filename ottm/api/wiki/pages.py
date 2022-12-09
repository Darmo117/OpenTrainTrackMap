"""This module defines functions to interact with the wiki’s database."""
import urllib.parse

import django.core.handlers.wsgi as dj_wsgi
import django.db.transaction as dj_db_trans

from . import constants, namespaces
from .. import auth, errors, permissions
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
    """Escape all URL special characters from the given page title.

    :param title: Page title to encode.
    :return: The encoded page title.
    """
    return urllib.parse.quote(title.replace(' ', '_'), safe='/:')


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


def get_edit_notice(user: models.User, language: settings.UILanguage) -> str:
    """Return the rendered edit notice from "Interface:EditNotice/<lang_code>".

    :param user: Current user.
    :param language: Page’s language.
    :return: The rendered edit notice.
    """
    return get_interface_page('EditNotice', user, language)


def get_new_page_notice(user: models.User, language: settings.UILanguage) -> str:
    """Return the rendered edit notice from "Interface:NewPageNotice/<lang_code>".

    :param user: Current user.
    :param language: Page’s language.
    :return: The rendered new page notice.
    """
    return get_interface_page('NewPageNotice', user, language)


def get_interface_page(title: str, user: models.User = None, language: settings.UILanguage = None,
                       render: bool = True) -> str:
    """Return the rendered interface page from "Interface:<title>/<lang_code>" if language is defined,
    "Interface:<title>" otherwise.

    :param title: Interface page title.
    :param user: Current user. May be None if render=False.
    :param language: Page’s language. May be None if no localized subpage exists.
    :param render: Whether to render the page’s content.
    :return: The rendered notice.
    """
    if language:
        title += f'/{language.code}'
    try:
        page = models.Page.objects.get(namespace_id=namespaces.NS_INTERFACE.id, title=title)
    except models.Page.DoesNotExist:
        return ''
    return render_wikicode(page, user, language) if render else page.get_content()


@dj_db_trans.atomic
def edit_page(request: dj_wsgi.WSGIRequest | None, author: models.User, page: models.Page, content: str,
              comment: str = None, minor_edit: bool = False, follow: bool = False, section_id: str = None):
    """Submit a new revision for the given page.
    If the page does not exist, it is created.

    :param request: Client request. May be None for internal calls.
    :param author: Edit’s author.
    :param page: Page to edit.
    :param content: New content of the page.
    :param comment: Edit’s comment.
    :param minor_edit: Whether to mark this revision as minor.
    :param follow: Whether the user wants to follow the page.
    :param section_id: ID of the edited page section. Not yet available.
    :raise MissingPermissionError: If the user cannot edit the page.
    :raise ConcurrentWikiEditError: If another edit was made on the same page before this edit.
    :raise ValueError: If the request is None and the user is anonymous.
    """
    if not page.can_user_edit(author):
        raise errors.MissingPermissionError(permissions.PERM_WIKI_EDIT)
    if False:  # TODO check if another edit was made while editing
        raise errors.ConcurrentWikiEditError()
    if request:
        if author.is_anonymous:
            author = auth.get_or_create_anonymous_account_from_request(request)
        else:
            raise ValueError('missing request')
    # Set content type to correct value
    if (ct := _get_page_content_type(page)) != page.content_type:
        page.content_type = ct
    if not page.exists:
        page.save()
        # Add to log
        models.PageCreationLog(performer=author.internal_object, page=page).save()
    models.PageRevision(
        page=page,
        author=author.internal_object,
        comment=comment,
        is_minor=minor_edit,
        content=content,
    ).save()
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
def follow_page(user: models.User, page: models.Page, follow: bool) -> bool:
    """Make a user follow/unfollow the given page.

    :param user: The user.
    :param page: The page to add/remove to the user’s follow list.
    :param follow: Whether to add or remove the page from the user’s follow list.
    :return: True if the operation was successful, false otherwise.
    """
    if user.is_anonymous:
        return False
    user_follows = page.is_user_following(user)
    if follow and not user_follows:
        models.PageFollowStatus(
            user=user.internal_object,
            page_namespace_id=page.namespace_id,
            page_title=page.title,
        ).save()
    elif not follow and user_follows:
        try:
            models.PageFollowStatus.objects.get(user=user, page_namespace_id=page.namespace_id,
                                                page_title=page.title).delete()
        except models.PageFollowStatus.DoesNotExist:
            return False
    return True
