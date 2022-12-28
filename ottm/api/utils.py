"""This module defines utility functions."""
import datetime as _dt
import math as _math

from django.conf import settings as _dj_settings
import pytz as _pytz


def escape_html(s: str) -> str:
    """Escape all '<' and '>' characters to their HTML entity."""
    return s.replace('<', '&lt;').replace('>', '&gt;')


def clamp(v: int | float, mini: int | float = -_math.inf, maxi: int | float = _math.inf) -> int | float:
    """Clamp a value between two bounds.

    :param v: The value to clamp.
    :param mini: The minimum value.
    :param maxi: The maximum value.
    :return: The clamped value.
    """
    return max(min(v, maxi), mini)


def normalize_line_returns(s: str) -> str:
    """Replace any CRLF and CR by LF."""
    return s.replace('\r\n', '\n').replace('\r', '\n')


def now() -> _dt.datetime:
    """Return the current UTC time."""
    return _dt.datetime.now().astimezone(_pytz.timezone(_dj_settings.TIME_ZONE))
