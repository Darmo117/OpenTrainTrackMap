"""This module defines template tags for the wiki."""
import datetime
import typing as typ

import django.core.paginator as dj_paginator
import django.template as dj_template
import django.utils.safestring as dj_safe

from . import ottm
from .. import models
from ..api.wiki import pages as w_pages

register = dj_template.Library()


@register.filter
def wiki_url_escape_page_title(value: str) -> str:
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
def wiki_inner_link(context: dict[str, typ.Any], page_title: str, text: str = None, no_redirect: bool = False) -> str:
    """Render an internal link.

    :param context: Page context.
    :param page_title: Title of the page to link.
    :param text: Link’s text. May be None.
    :param no_redirect: Whether to insert a noredirect GET argument.
    :return: The rendered link.
    """
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_static(context: dict[str, typ.Any], page_title: str) -> str:
    """Return the static resource link for the given wiki page.

    :param context: Page context.
    :param page_title: Title of the page to get the static resource from.
    :return: The resource’s link.
    """
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_format_date(context: dict[str, typ.Any], date: datetime.datetime) -> str:
    """Format the given date according to the context’s language.

    :param context: Page context.
    :param date: Date to format.
    :return: The formatted date.
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
