"""This module defines OTTM’s template tags."""
import datetime as _dt
import typing as _typ

import django.template as _dj_template
import django.utils.safestring as _dj_safe
import pytz as _pytz

from .. import page_handlers as _ph
from ..api import auth as _auth

register = _dj_template.Library()
TemplateContext = dict[str, _typ.Any]


@register.simple_tag(takes_context=True)
def ottm_translate(context: TemplateContext, key: str, **kwargs) -> str:
    """Translate the given key.

    :param context: Page context.
    :param key: Key to translate.
    :param kwargs: Translation’s arguments.
    :return: The translated text or the key in it is undefined for the current language.
    """
    ottm_context: _ph.PageContext = context['context']
    return _dj_safe.mark_safe(ottm_context.language.translate(key, **kwargs))


@register.simple_tag(takes_context=True)
def ottm_format_time(context: TemplateContext, date: _dt.datetime, timezone: str = None) -> str:
    """Format the given time.

    :param context: Page context.
    :param date: Date to format.
    :param timezone: Optional timezone name.
    :return: The formatted date.
    """
    ottm_context: _ph.PageContext = context['context']
    if timezone:
        tz = _pytz.timezone(timezone)
    else:
        tz = ottm_context.user.prefered_timezone
    date = date.astimezone(tz)
    iso_date = date.strftime('%H:%M')
    # language=HTML
    return _dj_safe.mark_safe(f'<time datetime="{iso_date}">{iso_date}</time>')


@register.simple_tag(takes_context=True)
def ottm_format_date(context: TemplateContext, date: _dt.datetime, timezone: str = None) -> str:
    """Format the given date according to the context’s language.

    :param context: Page context.
    :param date: Date to format.
    :param timezone: Optional timezone name.
    :return: The formatted date.
    """
    ottm_context: _ph.PageContext = context['context']
    if timezone:
        tz = _pytz.timezone(timezone)
    else:
        tz = ottm_context.user.prefered_timezone
    date = date.astimezone(tz)
    formated_date = ottm_context.language.format_datetime(date, ottm_context.user.prefered_datetime_format)
    iso_date = date.strftime('%Y-%m-%d %H:%M:%S%z')
    # language=HTML
    return _dj_safe.mark_safe(f'<time datetime="{iso_date}">{formated_date}</time>')


@register.simple_tag(takes_context=True)
def ottm_format_number(context: TemplateContext, n: int | float, value_only: bool = False) -> str:
    """Format the given number according to the context’s language.

    :param context: Page context.
    :param n: Number to format. May be an int or float.
    :param value_only: Whether to only return the formatted value.
    :return: The formatted number.
    """
    ottm_context: _ph.PageContext = context['context']
    s = ottm_context.language.format_number(n)
    # language=HTML
    return _dj_safe.mark_safe(f'<data value="{n}">{s}</data>') if not value_only else s


@register.simple_tag(takes_context=True)
def ottm_user_type_icon(context: TemplateContext, username: str) -> str:
    """Return the account type icon for the user that matches the given username.

    :param context: Page context.
    :param username: Username of the user.
    :return: The icon.
    """
    ottm_context: _ph.PageContext = context['context']
    user = _auth.get_user_from_name(username)
    if not user:
        key = 'page.user_profile.statistics.status_non_existent'
        icon = 'diameter-variant'
    elif not user.is_authenticated:
        key = 'page.user_profile.statistics.status_anonymous'
        icon = 'incognito'
    elif user.is_bot:
        key = 'page.user_profile.statistics.status_bot'
        icon = 'robot-happy-outline'
    else:
        key = 'page.user_profile.statistics.status_user'
        icon = 'account'
    tooltip = ottm_context.language.translate(key)
    # language=HTML
    return _dj_safe.mark_safe(f'<span class="mdi mdi-{icon}" title="{tooltip}"></span>')
