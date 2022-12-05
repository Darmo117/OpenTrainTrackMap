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
    return dj_safe.mark_safe(w_pages.url_encode_page_title(value))


@register.simple_tag(takes_context=True)
def wiki_translate(context: dict[str, typ.Any], key: str) -> str:
    return ottm.ottm_translate(context, 'wiki.' + key)


@register.simple_tag(takes_context=True)
def wiki_inner_link(context: dict[str, typ.Any], page_title: str, text: str = None, no_redirect: bool = False) -> str:
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_static(context: dict[str, typ.Any], page_title: str) -> str:
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_format_date(context: dict[str, typ.Any], date: datetime.datetime) -> str:
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_diff_link(context: dict[str, typ.Any], revision: models.PageRevision, against: str,
                   show_nav_link: bool = True) -> str:
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
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_page_list(context: dict[str, typ.Any], pages: dj_paginator.Paginator, paginate: bool = True) -> str:
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_revisions_list(context: dict[str, typ.Any], revisions: dj_paginator.Paginator, mode: str) -> str:
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_format_log_entry(context: dict[str, typ.Any], log_entry) -> str:
    return ''  # TODO
