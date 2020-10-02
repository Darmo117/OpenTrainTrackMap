from __future__ import annotations

import dataclasses
import typing as typ


@dataclasses.dataclass
class PageContext:
    site_name: str
    noindex: bool
    user: typ.Any  # FIXME annotate correctly

    def __post_init__(self):
        self._context = None

    def __getattr__(self, item):
        if self._context:
            return getattr(self._context, item)
        raise AttributeError(item)
