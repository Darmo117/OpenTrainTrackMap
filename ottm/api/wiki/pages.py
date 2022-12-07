import urllib.parse

import django.core.handlers.wsgi as dj_wsgi
import django.db.transaction as dj_db_trans

from . import namespaces
from .. import errors, permissions, auth
from ... import models

MAIN_PAGE_TITLE = namespaces.NS_WIKI.get_full_page_title('Main Page')


def split_title(title: str) -> tuple[namespaces.Namespace, str]:
    ns_id = 0
    if namespaces.SEPARATOR in title:
        a, b = title.split(namespaces.SEPARATOR, maxsplit=1)
        if ns := namespaces.resolve_name(a):
            ns_id = ns.id
            page_title = b
        else:
            page_title = title
    else:
        page_title = title
    return namespaces.NAMESPACES[ns_id], page_title


def get_correct_title(raw_title: str) -> str:
    return urllib.parse.unquote(raw_title.replace('_', ' '))


def url_encode_page_title(title: str) -> str:
    """Escape all URL special characters from the given page title.

    :param title: Page title to encode.
    :return: The encoded page title.
    """
    return urllib.parse.quote(title.replace(' ', '_'), safe='/:')


def get_page(ns: namespaces.Namespace, title: str) -> models.Page:
    try:
        return models.Page.objects.get(namespace_id=ns.id, title__iexact=title)
    except models.Page.DoesNotExist:
        return models.Page(
            namespace_id=ns.id,
            title=title,
        )


def get_js_config(page: models.Page, action: str) -> dict:
    return {
        'pageNamespaceID': page.namespace.id,
        'pageNamespaceName': page.namespace.name,
        'pageTitle': page.title,
        'action': action,
    }


def render_wikicode(code: str) -> str:
    pass  # TODO


def get_edit_notice() -> str:
    return ''  # TODO


@dj_db_trans.atomic
def edit_page(request: dj_wsgi.WSGIRequest, author: models.User, page: models.Page, content: str, comment: str = None,
              minor_edit: bool = False, follow: bool = False, section_id: str = None):
    if not page.can_user_edit(author):
        raise errors.MissingPermissionError(permissions.PERM_WIKI_EDIT)
    if False:  # TODO check if another edit was made while editing
        raise errors.ConcurrentWikiEditError()
    if author.is_anonymous:
        author = auth.get_or_create_anonymous_account_from_request(request)
    if not page.exists:
        page.save()
    models.PageRevision(
        page=page,
        author=author.internal_user,
        comment=comment,
        is_minor=minor_edit,
        content=content,
    ).save()
    follow_page(author, page, follow)
    # TODO add to creation and edit journals


@dj_db_trans.atomic
def follow_page(user: models.User, page: models.Page, follow: bool) -> bool:
    if user.is_anonymous:
        return False
    user_follows = page.is_user_following(user)
    if follow and not user_follows:
        models.PageWatchlist(
            user=user.internal_user,
            page_namespace_id=page.namespace_id,
            page_title=page.title,
        ).save()
    elif not follow and user_follows:
        try:
            models.PageWatchlist.objects.get(user=user, page_namespace_id=page.namespace_id,
                                             page_title=page.title).delete()
        except models.PageWatchlist.DoesNotExist:
            return False
    return True
