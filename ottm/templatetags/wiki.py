import django.template as dj_template
import django.utils.safestring as dj_safe

from ..api.wiki import namespaces, pages

register = dj_template.Library()


@register.simple_tag
def wiki_page_title_url(value: str) -> str:
    namespace_id, title = value.split(',', maxsplit=1)
    page_title = namespaces.NAMESPACES[int(namespace_id)].get_full_page_title(title)
    return dj_safe.mark_safe(pages.url_encode_page_title(page_title))  # TODO check if encode necessary here
