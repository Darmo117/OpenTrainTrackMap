"""This module defines template tags for the wiki."""
import typing as typ

import django.core.paginator as dj_paginator
import django.template as dj_template
import django.utils.safestring as dj_safe

from . import ottm
from .. import models, page_context
from ..api.wiki import menus, pages as w_pages, parser

register = dj_template.Library()


@register.filter
def wiki_url_escape(value: str) -> str:
    """Convert the given page name to a URL-safe value."""
    return dj_safe.mark_safe(w_pages.url_encode_page_title(value))


@register.simple_tag(takes_context=True)
def wiki_translate(context: dict[str, typ.Any], key: str, **kwargs) -> str:
    """Translate the given key. The prefix 'wiki.' is appended automatically.

    :param context: Page context.
    :param key: Key to translate.
    :param kwargs: Translation’s arguments.
    :return: The translated text or the key in it is undefined for the current language.
    """
    return ottm.ottm_translate(context, 'wiki.' + key, **kwargs)


@register.simple_tag(takes_context=True)
def wiki_inner_link(
        context: dict[str, typ.Any],
        page_title: str,
        text: str = None,
        tooltip: str = None,
        anchor: str = None,
        url_params: str = None,
        css_classes: str = None,
        access_key: str = None,
        ignore_current_title: bool = False,
        no_red_link: bool = False,
        only_url: bool = False,
        new_tab: bool = False,
) -> str:
    """Render an internal link.

    :param context: Page context.
    :param page_title: Title of the page to link.
    :param text: Link’s text. May be None.
    :param tooltip: Link’s tooltip.
    :param anchor: Link’s anchor.
    :param url_params: Additional URL parameters.
    :param css_classes: Additional CSS classes.
    :param access_key: Link’s access key.
    :param ignore_current_title: Whether to ignore the current page’s title when rendering the link.
    :param no_red_link: Whether to keep the link the default color even if the target page does not exist.
    :param only_url: Whether to return the URL instead of rendering it.
    :param new_tab: Whether to add target="_blank" to link’s tag.
    :return: The rendered link.
    """
    wiki_context: page_context.WikiPageContext = context.get('context')
    current_title = wiki_context.page.full_title if not ignore_current_title else None
    classes = css_classes.split() if css_classes else []
    if url_params:
        params = {k: v for k, v in map(lambda v: v.split('='), url_params.split('&'))}
    else:
        params = {}
    link = parser.Parser.format_internal_link(
        page_title,
        wiki_context.language,
        text=text,
        tooltip=tooltip,
        anchor=anchor,
        url_params=params,
        css_classes=classes,
        access_key=access_key,
        current_page_title=current_title,
        no_red_link=no_red_link,
        only_url=only_url,
        open_in_new_tab=new_tab,
    )
    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wiki_static(context: dict[str, typ.Any], page_title: str) -> str:
    """Return the static resource link for the given wiki page.

    :param context: Page context.
    :param page_title: Title of the page to get the static resource from.
    :return: The resource’s link.
    """
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_diff_link(context: dict[str, typ.Any], revision: models.PageRevision, against: str,
                   show_nav_link: bool = True) -> str:
    """Render a revision’s diff link.

    :param context: Page context.
    :param revision: Revision to get data from.
    :param against:
    :param show_nav_link:
    :return: The rendered diff link.
    """
    match against:
        case 'previous':
            pass
        case 'current':
            pass
        case 'next':
            pass
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_revision_comment(context: dict[str, typ.Any], revision: models.PageRevision) -> str:
    """Format a revision’s comment.

    :param context: Page context.
    :param revision: The revision to render the comment of.
    :return: The formatted comment.
    """
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_page_list(context: dict[str, typ.Any], pages: dj_paginator.Paginator, paginate: bool = True) -> str:
    """Render a list of pages.

    :param context: Page context.
    :param pages: A Paginator object containing the pages.
    :param paginate: Whether to add pagination buttons.
    :return: The rendered list.
    """
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_revisions_list(context: dict[str, typ.Any], revisions: dj_paginator.Paginator, mode: str) -> str:
    """Render a list of revisions.

    :param context: Page context.
    :param revisions: A Paginator object containing the revisions.
    :param mode: Specifies how the revisions should be rendered. Either 'history' or 'contributions'.
    :return: The rendered revisions list.
    """
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_format_log_entry(context: dict[str, typ.Any], log_entry) -> str:
    """Format a log entry.

    :param context: Page context.
    :param log_entry: The log entry to format.
    :return: The formatted log entry.
    """
    return ''  # TODO


@register.inclusion_tag('ottm/wiki/tags/side_menu.html', takes_context=True)
def wiki_side_menu(context: dict[str, typ.Any], menu_id: str) -> dict[str, typ.Any]:
    """Format the menu with the given ID.

    :param context: Page context.
    :param menu_id: Menu’s ID.
    :return: The formatted menu.
    """
    wiki_context: page_context.WikiPageContext = context.get('context')
    return {'menus': menus.get_menus(wiki_context, menu_id), 'dark_mode': wiki_context.dark_mode}
