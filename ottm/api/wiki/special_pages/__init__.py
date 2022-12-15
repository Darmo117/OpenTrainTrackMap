"""This package defines the wiki’s special pages.
Special pages are pages that are not stored in the database.
They are used to manage the wiki and may require specific permissions.
"""
import importlib as _il
import os.path as _os_path
import pathlib as _pathlib

from ._core import *

SPECIAL_PAGES: dict[str, SpecialPage] = {}
"""Collection of all loaded special pages."""


def init():
    """Load and initialize all special pages from this package."""
    # Import all special pages from this package
    for f in _pathlib.Path(__file__).parent.glob('_*.py'):
        if f.is_file() and f.name not in ('__init__.py', '_core.py'):
            module = _il.import_module('.' + _os_path.splitext(f.name)[0], package=__name__)
            for k, v in module.__dict__.items():
                if k[0] != '_' and isinstance(v, type) and issubclass(v, SpecialPage):
                    # noinspection PyArgumentList
                    sp = v()
                    SPECIAL_PAGES[sp.name] = sp


init()
