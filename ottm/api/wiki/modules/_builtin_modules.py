import bisect as _b
import calendar as _cal
import collections as _colls
import colorsys as _cs
import copy as _c
import datetime as _dt
import fractions as _f
import html as _html
import html.entities as _html_entities
import html.parser as _html_parser
import itertools as _it
import json as _json
import math as _m
import numbers as _n
import random as _r
import re as _re
import statistics as _stats
import string as _s
import textwrap as _tw
import time as _t
import typing as _typ
import unicodedata as _ud

import pytz as _pytz


class BuiltinModule:
    def __init__(self, name: str, doc: str, properties: dict[str, _typ.Any]):
        self.__name__ = name
        self.__qualname__ = name
        self._name = name
        self.__doc__ = doc
        self._properties = properties

    def __dir__(self) -> _typ.Iterable[str]:
        return self._properties.keys()

    def __getattr__(self, item: str):
        return self._properties[item]

    def __repr__(self):
        return f'<built-in module "{self._name}">'


def get_module(name: str) -> BuiltinModule:
    if name not in _MODULES:
        raise ImportError(f'undefined built-in module "{name}"')
    return _MODULES[name]


_MODULES: dict[str, BuiltinModule] = {}


def _load_module(module, submodules: dict[str, BuiltinModule] = (),
                 blacklist: list[str] = (), whitelist: list[str] = (),
                 register: bool = True) -> BuiltinModule:
    if hasattr(module, '__all__') and not whitelist:
        whitelist = module.__all__
    properties = {k: v for k, v in module.__dict__.items()
                  if not k.startswith('_') and k not in blacklist and k in whitelist}
    properties.update(submodules)
    m = BuiltinModule(module.__name__, module.__doc__, properties)
    if register:
        _MODULES[module.__name__] = m
    return m


# TODO import geopy and/or geographiclib
_load_module(_b)
_load_module(_cal)
_load_module(_colls, blacklist=['UserDict', 'UserList', 'UserString'])
_load_module(_cs)
_load_module(_c)
_load_module(_dt)
_load_module(_f)
_load_module(_html, submodules={
    'entities': _load_module(_html_entities, register=False),
    'parser': _load_module(_html_parser, register=False),
})
_load_module(_it)
_load_module(_json, blacklist=['dump', 'load'])
_load_module(_n)
_load_module(_m)
_load_module(_pytz)
_load_module(_r)
_load_module(_re)
_load_module(_stats)
_load_module(_s)
_load_module(_tw)
_load_module(_t)
_load_module(_ud, blacklist=['UCD'])
# TODO module to manipulate pages and get wiki stats
# TODO module for i18n
