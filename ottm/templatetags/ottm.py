"""This module defines OTTM’s template tags."""
import datetime as _dt
import typing as _typ

import django.template as _dj_template
import django.utils.safestring as _dj_safe

from .. import page_context as _pc

register = _dj_template.Library()


@register.simple_tag(takes_context=True)
def ottm_translate(context: dict[str, _typ.Any], key: str, **kwargs) -> str:
    """Translate the given key.

    :param context: Page context.
    :param key: Key to translate.
    :param kwargs: Translation’s arguments.
    :return: The translated text or the key in it is undefined for the current language.
    """
    ottm_context: _pc.PageContext = context['context']
    return _dj_safe.mark_safe(ottm_context.language.translate(key, **kwargs))


@register.simple_tag(takes_context=True)
def ottm_format_date(context: dict[str, _typ.Any], date: _dt.datetime) -> str:
    """Format the given date according to the context’s language.

    :param context: Page context.
    :param date: Date to format.
    :return: The formatted date.
    """
    ottm_context: _pc.PageContext = context['context']
    date = date.astimezone(ottm_context.user.prefered_timezone)
    formated_date = ottm_context.language.format_datetime(date, ottm_context.user.prefered_datetime_format)
    iso_date = date.strftime('%Y-%m-%d %H:%M:%S%z')
    return _dj_safe.mark_safe(f'<time id="last_edit_date" datetime="{iso_date}">{formated_date}</time>')
