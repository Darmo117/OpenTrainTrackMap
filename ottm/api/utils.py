"""This module defines utility functions."""


def escape_html(s: str) -> str:
    """Escape all '<' and '>' characters to their HTML entity."""
    return s.replace('<', '&lt;').replace('>', '&gt;')
