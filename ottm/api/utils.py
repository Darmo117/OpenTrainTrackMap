"""This module defines utility functions."""
import datetime
import math

import pytz


def escape_html(s: str) -> str:
    """Escape all '<' and '>' characters to their HTML entity."""
    return s.replace('<', '&lt;').replace('>', '&gt;')


def clamp(v: int | float, mini: int | float = -math.inf, maxi: int | float = math.inf) -> int | float:
    """Clamp a value between two bounds.

    :param v: The value to clamp.
    :param mini: The minimum value.
    :param maxi: The maximum value.
    :return: The clamped value.
    """
    return max(min(v, maxi), mini)


def now() -> datetime.datetime:
    """Return the current UTC time."""
    return datetime.datetime.now().astimezone(pytz.UTC)
