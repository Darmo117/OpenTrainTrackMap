"""This module defines functions to interact with the wiki’s database."""
import urllib.parse

import django.core.handlers.wsgi as dj_wsgi
import django.db.transaction as dj_db_trans

from . import namespaces
from .. import errors, permissions, auth
from ... import models

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
        return models.Page.objects.get(namespace_id=ns.id, title__iexact=title)
    except models.Page.DoesNotExist:
        return models.Page(
            namespace_id=ns.id,
            title=title,
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
    }


def render_wikicode(code: str, user: models.User) -> str:
    """Render the given wikicode.

    :param code: The wikicode to render.
    :param user: The current user.
    :return: The rendered wikicode.
    """
    pass  # TODO


def get_edit_notice() -> str:
    """Return the rendered edit notice from "Interface:EditNotice"."""
    return ''  # TODO


@dj_db_trans.atomic
def edit_page(request: dj_wsgi.WSGIRequest, author: models.User, page: models.Page, content: str, comment: str = None,
              minor_edit: bool = False, follow: bool = False, section_id: str = None):
    """Submit a new revision for the given page.
    If the page does not exist, it is created.

    :param request: Client request.
    :param author: Edit’s author.
    :param page: Page to edit.
    :param content: New content of the page.
    :param comment: Edit’s comment.
    :param minor_edit: Whether to mark this revision as minor.
    :param follow: Whether the user wants to follow the page.
    :param section_id: ID of the edited page section. Not yet available.
    :raise MissingPermissionError: If the user cannot edit the page.
    :raise ConcurrentWikiEditError: If another edit was made on the same page before this edit.
    """
    if not page.can_user_edit(author):
        raise errors.MissingPermissionError(permissions.PERM_WIKI_EDIT)
    if False:  # TODO check if another edit was made while editing
        raise errors.ConcurrentWikiEditError()
    if author.is_anonymous:
        author = auth.get_or_create_anonymous_account_from_request(request)
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
