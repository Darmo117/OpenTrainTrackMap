import urllib.parse

from . import namespaces
from ... import models

MAIN_PAGE_TITLE = namespaces.NS_META.get_full_page_title('Main Page')


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
