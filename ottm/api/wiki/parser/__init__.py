"""This module defines the wikicode parser."""
import dataclasses as _dataclasses
import datetime as _dt
import inspect as _inspect
import random as _random
import re as _re
import time as _time
import urllib.parse as _url_parse

import django.shortcuts as _dj_scut

from . import _magic_variables as _mv
from .. import constants as _w_cons, namespaces as _w_ns, pages as _w_pages
from ... import utils as _utils
from .... import models as _models, settings as _settings


@_dataclasses.dataclass(frozen=True)
class ParsingMetadata:
    """Wrapper for metadata of a parsed page."""
    links: list[tuple[int, str]]
    categories: list[tuple[str, str | None]]
    parse_duration: int
    parse_date: _dt.datetime
    size_before: int
    size_after: int


@_dataclasses.dataclass(frozen=True)
class HTMLTagDefinition:
    block: bool = False
    void: bool = False


@_dataclasses.dataclass(frozen=True)
class CustomTagAttribute:
    name: str
    optional: bool = True


@_dataclasses.dataclass(frozen=True)
class CustomTagDefinition(HTMLTagDefinition):
    attributes: list[CustomTagAttribute] = ()


class Parser:
    """The wikicode parser."""
    # TODO max text size

    NOWIKI_TAG_REGEX = _re.compile('<nowiki>(.+?)</nowiki>', _re.DOTALL)

    HTML_TAGS = {
        'a': HTMLTagDefinition(),
        'abbr': HTMLTagDefinition(),
        'address': HTMLTagDefinition(),
        'area': HTMLTagDefinition(void=True),
        'aside': HTMLTagDefinition(block=True),
        'b': HTMLTagDefinition(),
        'bdi': HTMLTagDefinition(),
        'bdo': HTMLTagDefinition(),
        'blockquote': HTMLTagDefinition(block=True),
        'br': HTMLTagDefinition(void=True),
        'caption': HTMLTagDefinition(),
        'cite': HTMLTagDefinition(),
        'code': HTMLTagDefinition(),
        'col': HTMLTagDefinition(void=True),
        'colgroup': HTMLTagDefinition(),
        'data': HTMLTagDefinition(),
        'dd': HTMLTagDefinition(block=True),
        'del': HTMLTagDefinition(),
        'details': HTMLTagDefinition(block=True),
        'dfn': HTMLTagDefinition(),
        'div': HTMLTagDefinition(block=True),
        'dl': HTMLTagDefinition(block=True),
        'dt': HTMLTagDefinition(block=True),
        'em': HTMLTagDefinition(),
        'hr': HTMLTagDefinition(block=True, void=True),
        'i': HTMLTagDefinition(),
        'ins': HTMLTagDefinition(),
        'kbd': HTMLTagDefinition(),
        'label': HTMLTagDefinition(),
        'li': HTMLTagDefinition(block=True),
        'map': HTMLTagDefinition(),
        'mark': HTMLTagDefinition(),
        'meter': HTMLTagDefinition(),
        'nav': HTMLTagDefinition(),
        'ol': HTMLTagDefinition(),
        'p': HTMLTagDefinition(block=True),
        'pre': HTMLTagDefinition(block=True),
        'progress': HTMLTagDefinition(),
        'q': HTMLTagDefinition(),
        'rp': HTMLTagDefinition(),
        'rt': HTMLTagDefinition(),
        'ruby': HTMLTagDefinition(),
        's': HTMLTagDefinition(),
        'samp': HTMLTagDefinition(),
        'section': HTMLTagDefinition(block=True),
        'small': HTMLTagDefinition(),
        'span': HTMLTagDefinition(),
        'strong': HTMLTagDefinition(),
        'sub': HTMLTagDefinition(),
        'summary': HTMLTagDefinition(block=True),
        'table': HTMLTagDefinition(block=True),
        'tbody': HTMLTagDefinition(block=True),
        'td': HTMLTagDefinition(block=True),
        'template': HTMLTagDefinition(block=True),
        'tfoot': HTMLTagDefinition(block=True),
        'th': HTMLTagDefinition(block=True),
        'thead': HTMLTagDefinition(block=True),
        'time': HTMLTagDefinition(),
        'tr': HTMLTagDefinition(block=True),
        'u': HTMLTagDefinition(),
        'ul': HTMLTagDefinition(block=True),
        'var': HTMLTagDefinition(),
        'wbr': HTMLTagDefinition(void=True),
    }
    CUSTOM_TAGS = {
        'gallery': CustomTagDefinition(block=True, attributes=[
            CustomTagAttribute(name='mode'),
            CustomTagAttribute(name='caption'),
            CustomTagAttribute(name='widths'),
            CustomTagAttribute(name='heights'),
            CustomTagAttribute(name='perrow'),  # Nb of images per row
            CustomTagAttribute(name='showthumbnails'),
        ]),
        'ref': CustomTagDefinition(attributes=[
            CustomTagAttribute(name='name', optional=False),
            CustomTagAttribute(name='group'),
        ]),
        'references': CustomTagDefinition(block=True, void=True, attributes=[
            CustomTagAttribute(name='group'),
        ]),
    }
    PARSER_FUNCTIONS: dict[str, _mv.MagicVariable] = {
        variable.name: variable for variable in (
            mv_class()
            for class_name, mv_class in _mv.__dict__.items()
            if (not class_name.startswith('_')
                and isinstance(mv_class, type)
                and issubclass(mv_class, _mv.MagicVariable)
                and not _inspect.isabstract(mv_class))
        )
    }

    def __init__(self, page: _models.Page):
        self._page = page
        # noinspection PyTypeChecker
        self._placeholder_index = _random.randint(1e12, 1e13 - 1)  # Random start index
        self._nowiki_placeholders: dict[str, str] = {}
        self._custom_tags_placeholders: dict[str, str] = {}
        self._metadata = None

    @property
    def output_metadata(self) -> ParsingMetadata | None:
        """Metadata for the parsed page."""
        return self._metadata

    def parse(self, wikicode: str) -> str:
        """Parse the given wikicode."""
        start_time = _time.time() * 1000
        links = []
        categories = []
        size_before = len(wikicode.encode('utf-8'))

        parsed = self._extract_nowiki_tags(wikicode)
        parsed = self._sanitize_html_tags(parsed)
        parsed = self._substitute_transclusion_parameters(parsed)
        parsed = self._substitute_parser_functions(parsed)
        parsed = self._transclude(parsed)
        parsed = self._extract_custom_tags(parsed)
        parsed = self._parse(parsed)
        parsed = self._substitute_custom_tags_placeholders(parsed)
        parsed = self._substitute_nowiki_placeholders(parsed)

        self._metadata = ParsingMetadata(
            links=links,
            categories=categories,
            parse_duration=round((_time.time() * 1000) - start_time),
            parse_date=_utils.now(),
            size_before=size_before,
            size_after=len(parsed.encode('utf-8')),
        )
        return parsed

    def _sanitize_html_tags(self, wikicode: str) -> str:
        """Sanitize all disallowed HTML tags, i.e. replace < characters with &lt; where necessary."""

        def repl(m: _re.Match[str]) -> str:
            match = m.group(0)
            slash = m.group(1)
            group = m.group(2)
            if group not in self.HTML_TAGS and group not in self.CUSTOM_TAGS:
                return f'&lt;/{group}' if slash else f'&lt;{group}'
            return match

        return _re.sub(r'<(/?)(\w+)', repl, _re.sub(r'<(?=[^\w/])', '&lt;', wikicode))

    def _extract_nowiki_tags(self, wikicode: str) -> str:
        """Replace all <nowiki></nowiki> tags by placeholders."""

        def repl(m: _re.Match[str]) -> str:
            placeholder = f'`$:!PLACEHOLDER-nowiki-{self._placeholder_index}!:$`'
            self._nowiki_placeholders[placeholder] = m.group(1)
            self._placeholder_index += 1
            return placeholder

        return self.NOWIKI_TAG_REGEX.sub(repl, wikicode)

    def _substitute_transclusion_parameters(self, wikicode: str) -> str:
        """Substitute all transclusion parameters."""
        return wikicode  # TODO

    def _substitute_parser_functions(self, wikicode: str) -> str:
        """Evaluate all parser functions and replace them with their return value."""
        prefix = '{{#'
        prefix_l = len(prefix)
        in_function_name = False
        braces_nb = 0
        function_name = ''
        function_args = ''
        buffer = ''
        i = 0
        wikicode_l = len(wikicode)
        while i < wikicode_l:
            c = wikicode[i]
            if i < wikicode_l - prefix_l and wikicode[i:i + prefix_l] == prefix:
                in_function_name = True
                braces_nb = 1
                function_name = ''
                function_args = ''
                i += prefix_l
            elif in_function_name:
                if _re.fullmatch(r'\w', c):
                    function_name += c
                else:
                    in_function_name = False
                    if c != '|':
                        buffer += prefix + function_name
                        braces_nb = 0
                i += 1
            elif braces_nb != 0:
                if c == '}}':
                    braces_nb -= 1
                    i += 2
                elif c == '{{':
                    braces_nb += 1
                    i += 2
                else:
                    i += 1
                if braces_nb != 0:
                    function_args += c
                else:
                    buffer += self._substitute_parser_function(function_name, function_args)
            else:
                buffer += c
                i += 1

        if in_function_name:
            buffer += prefix + function_name
        elif braces_nb != 0:
            buffer += prefix + function_name
            if function_args:
                buffer += '|' + function_args

        return buffer

    def _substitute_parser_function(self, name: str, raw_args: str) -> str:
        if '{{#' in raw_args:
            raw_args = self._substitute_parser_functions(raw_args)
        if name not in self.PARSER_FUNCTIONS:
            return self._print_error(f'Undefined {name!r} parser function')
        args = [arg.strip().replace('{{!}}', '|') for arg in raw_args.split('|')]
        # TODO

    def _extract_custom_tags(self, wikicode: str) -> str:
        """Replace all custom tags by placeholders."""
        return wikicode  # TODO

    def _transclude(self, wikicode: str) -> str:
        """Transclude all templates and other pages."""
        return wikicode  # TODO

    def _parse(self, wikicode: str) -> str:
        """Parse the article (links, titles, paragraphs, etc.)."""
        return wikicode  # TODO

    def _substitute_custom_tags_placeholders(self, wikicode: str) -> str:
        """Replace all custom tag placeholders by their associated value."""
        return wikicode  # TODO

    def _substitute_nowiki_placeholders(self, wikicode: str):
        """Replace all nowiki placeholders with their associated value."""
        for placeholder, text in self._nowiki_placeholders.items():
            wikicode = wikicode.replace(placeholder, text.replace('<', '&lt;').replace('>', '&gt;'))
        return wikicode

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

    @staticmethod
    def get_redirect_link(page_title: str) -> str:
        """Generate the wikicode for a redirect link for the given page title.

        :param page_title: Page title to redirect to.
        :return: The redirect link wikicode.
        """
        return f'#REDIRECT[[{page_title}]]'
