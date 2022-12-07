"""This module defines utility template tags."""
import django.template as dj_template

_register = dj_template.Library()


@_register.filter
def replace(value: str, pattern: str) -> str:
    """Replace all occurences of a value by another in a string.

    :param value: The string to apply the operation to.
    :param pattern: The pattern in the format '<needle>,<replacement>'.
     The replacement may contain commas, the needle may not.
    :return: The transformed string.
    """
    needle, repl = pattern.split(',', maxsplit=1)
    return value.replace(needle, repl)
