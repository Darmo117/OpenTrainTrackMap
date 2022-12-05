import django.template as dj_template

register = dj_template.Library()


@register.filter
def replace(value: str, pattern: str) -> str:
    needle, repl = pattern.split(',', maxsplit=1)
    return value.replace(needle, repl)
