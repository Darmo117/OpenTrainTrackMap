"""This module defines the wikicode parser."""
import dataclasses as _dataclasses
import datetime as _dt
import random as _random
import time as _time
import urllib.parse as _url_parse

import django.shortcuts as _dj_scut

from . import constants as _w_cons, namespaces as _w_ns, pages as _w_pages
from .. import utils as _utils
from ... import models as _models, settings as _settings


@_dataclasses.dataclass(frozen=True)
class ParserMetadata:
    """Wrapper for metadata of a parsed page."""
    links: list[tuple[int, str]]
    categories: list[tuple[str, str | None]]
    parse_duration: int
    parse_date: _dt.datetime
    size_before: int
    size_after: int


class Parser:
    """The wikicode parser."""

    def __init__(self, page: _models.Page):
        self._page = page
        # noinspection PyTypeChecker
        self._placeholder_index = _random.randint(1e12, 1e13 - 1)
        self._nowiki = {}
        self._metadata = None

    @property
    def output_metadata(self) -> ParserMetadata | None:
        """Metadata for the parsed page."""
        return self._metadata

    def parse(self, wikicode: str) -> str:
        """Parse the given wikicode."""
        start_time = _time.time() * 1000
        links = []
        categories = []
        size_before = len(wikicode.encode('utf-8'))

        escaped = self._replace_nowiki(wikicode)

        parsed = escaped
        for placeholder, text in self._nowiki.items():
            parsed = parsed.replace(placeholder, text)

        self._metadata = ParserMetadata(
            links=links,
            categories=categories,
            parse_duration=round((_time.time() * 1000) - start_time),
            parse_date=_utils.now(),
            size_before=size_before,
            size_after=len(parsed.encode('utf-8')),
        )
        return parsed

    def _replace_nowiki(self, wikicode: str) -> str:
        """Replace all <nowiki></nowiki> tags by placeholders in the given wikicode."""
        res = ''
        buffer = ''
        stack = False
        i = 0
        len_nowiki = len('<nowiki>')
        len_w = len(wikicode)
        while i < len_w:
            if i < len_w - len_nowiki and wikicode[i:i + len_nowiki] == '<nowiki>':
                stack = True
                i += len_nowiki
            elif i < len_w - (len_nowiki + 1) and wikicode[i:i + len_nowiki + 1] == '</nowiki>':
                stack = False
                placeholder = f'`$:!PLACEHOLDER-{self._placeholder_index}!:$`'
                self._placeholder_index += 1
                self._nowiki[placeholder] = buffer
                buffer = ''
                res += placeholder
                i += len_nowiki + 1
            elif stack:
                buffer += wikicode[i]
                i += 1
            else:
                res += wikicode[i]
                i += 1
        if buffer:  # Case for non-closed tag
            res += '<nowiki>' + buffer
        return res

    @classmethod
    def format_internal_link(
            cls,
            page_title: str,
            language: _settings.UILanguage,
            text: str = None,
            tooltip: str = None,
            anchor: str = None,
            url_params: dict[str, str] = None,
            css_classes: list[str] = None,
            id_: str = None,
            access_key: str = None,
            current_page_title: str = None,
            no_red_link: bool = False,
            only_url: bool = False,
            open_in_new_tab: bool = False,
    ):
        url_params = url_params or {}
        page = _w_pages.get_page(*_w_pages.split_title(page_title))

        link_text = page.full_title if text is None else text

        if current_page_title == page.full_title and not anchor and not url_params:
            return f'<strong class="wiki-recursive-link">{link_text}</strong>' if not only_url else ''

        url = _dj_scut.reverse('ottm:wiki_page', kwargs={
            'raw_page_title': _w_pages.url_encode_page_title(page.full_title)
        })
        link_tooltip = tooltip or page.full_title

        if (page.exists or no_red_link
                or url_params.get('action') in (
                        _w_cons.ACTION_TALK, _w_cons.ACTION_INFO, _w_cons.ACTION_HISTORY, _w_cons.ACTION_RAW)):
            params = _url_parse.urlencode(url_params)
            if params:
                url += '?' + params
            if anchor:
                url += '#' + anchor
        else:
            if page.namespace != _w_ns.NS_SPECIAL:
                url += '?action=edit&red_link=1'
            paren = language.translate('wiki.link.red_link.tooltip')
            link_tooltip += f' ({paren})'

        if only_url:
            return url
        return cls.format_link(
            url,
            link_text,
            link_tooltip,
            page.exists,
            css_classes or [],
            id_=id_,
            access_key=access_key,
            external=open_in_new_tab,
        )

    @classmethod
    def format_link(
            cls,
            url: str,
            text: str,
            tooltip: str,
            page_exists: bool,
            css_classes: list[str],
            id_: str = None,
            access_key: str = None,
            external: bool = False,
            **data_attributes
    ):
        if not page_exists:
            css_classes = [*css_classes, 'wiki-red-link']
        attributes = {}
        if 'disabled' in css_classes:
            attributes['aria-disabled'] = 'true'
            url = ''
        if access_key:
            attributes['accesskey'] = access_key
        if external:
            text += ' <span class="mdi mdi-open-in-new"></span>'
            attributes['target'] = '_blank'
        for k, v in data_attributes.items():
            attributes[f'data-{k}'] = int(v) if isinstance(v, bool) else v
        if id_:
            attributes['id'] = id_
        attributes['href'] = url
        attributes['class'] = ' '.join(css_classes)
        attributes['title'] = tooltip
        attrs = ' '.join(f'{attr}="{value}"' for attr, value in attributes.items())
        link = f'<a {attrs}>{text}</a>'

        return link
