import django.template as dj_template
import django.utils.safestring as dj_safe

from .. import page_context

register = dj_template.Library()


@register.simple_tag(takes_context=True)
def ottm_translate(context: dict, key: str):
    ottm_context: page_context.PageContext = context['context']
    return dj_safe.mark_safe(ottm_context.user.prefered_language.translate(key))
