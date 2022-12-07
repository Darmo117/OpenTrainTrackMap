"""This module defines OTTM’s template tags."""
import typing as typ

import django.template as dj_template
import django.utils.safestring as dj_safe

from .. import page_context

register = dj_template.Library()


@register.simple_tag(takes_context=True)
def ottm_translate(context: dict[str, typ.Any], key: str, **kwargs) -> str:
    """Translate the given key.

    :param context: Page context.
    :param key: Key to translate.
    :param kwargs: Translation’s arguments.
    :return: The translated text or the key in it is undefined for the current language.
    """
    ottm_context: page_context.PageContext = context['context']
    return dj_safe.mark_safe(ottm_context.user.prefered_language.translate(key, **kwargs))
