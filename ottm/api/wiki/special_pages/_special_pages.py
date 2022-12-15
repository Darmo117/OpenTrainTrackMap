"""This module defines the special page listing all other special pages."""
import typing as _typ

from . import _core
from .... import requests as _requests


class SpecialPagesSpecialPage(_core.SpecialPage):
    """This special page lists all special pages."""

    def __init__(self):
        super().__init__('SpecialPages')

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        from . import SPECIAL_PAGES

        sections = {s.value: [] for s in _core.Section}
        for sp in SPECIAL_PAGES.values():
            if not sp.category:
                continue
            sections[sp.category.value].append(sp)
        for pages in sections.values():
            pages.sort(key=lambda p: p.name)
        return {
            'title_key': 'title',
            'special_page_sections': sections,
        }
