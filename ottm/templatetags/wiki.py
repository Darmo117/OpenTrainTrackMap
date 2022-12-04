import django.template as dj_template
import django.utils.safestring as dj_safe

from ..api.wiki import pages

register = dj_template.Library()


@register.simple_tag
def wiki_url_escape_page_title(value: str) -> str:
    return dj_safe.mark_safe(pages.url_encode_page_title(value))
