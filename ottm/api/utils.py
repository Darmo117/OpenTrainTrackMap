"""This module defines utility functions."""
import datetime

import pytz


def escape_html(s: str) -> str:
    """Escape all '<' and '>' characters to their HTML entity."""
    return s.replace('<', '&lt;').replace('>', '&gt;')


def now() -> datetime.datetime:
    """Return the current UTC time."""
    return datetime.datetime.now().astimezone(pytz.UTC)
