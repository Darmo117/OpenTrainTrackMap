"""This module defines the wikicode parser."""
import dataclasses as _dataclasses
import datetime as _dt
import inspect as _inspect
import random as _random
import re as _re
import time as _time
import urllib.parse as _url_parse

import django.shortcuts as _dj_scut

from . import _magic_variables as _mv, _parser_context as _pc, _template_tags as _tt
from .. import constants as _w_cons, namespaces as _w_ns, pages as _w_pages
from ... import utils as _utils, auth as _auth
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
    template_tag_error: bool


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


# TODO run on dedicated thread with timeout
class Parser:
    """The wikicode parser."""

    MAX_TEXT_LENGTH = 1e7  # Max number of parsed characters

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
    TEMPLATE_TAGS: dict[str, type[_tt.TemplateTag]] = {
        variable.name: variable for variable in (
            tt_class
            for class_name, tt_class in _tt.__dict__.items()
            if (not class_name.startswith('_')
                and isinstance(tt_class, type)
                and issubclass(tt_class, _tt.TemplateTag)
                and not _inspect.isabstract(tt_class))
        )
    }

    COMMENT_DELIMS = ('{#', '#}')
    EXPR_INSERT_DELIMS = ('{=', '=}')
    TEMPLATE_TAG_DELIMS = ('{%', '%}')

    def __init__(self, page: _models.Page, revision: _models.PageRevision = None):
        """Create a wikicode parser for the given page and revision.

        :param page: The page object.
        :param revision: The specific revision of the given page to parse. May be None when in edit preview mode.
        """
        self._page = page
        self._custom_tags_placeholders: dict[str, str] = {}
        user = _auth.get_user_from_name(page.base_name) if page.namespace == _w_ns.NS_USER else None
        # noinspection PyTypeChecker
        self._context = _pc.ParserContext(
            placeholder_index=_random.randint(1e12, 1e13 - 1),  # Random start index
            user=user,
            page=page,
            revision=revision,
            date=_utils.now(),
            display_title=page.full_title,
            default_sort_key=page.full_title,
        )
        self._template_tag_error = False
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

        # parsed = self._parse_template_tags(wikicode)
        # parsed = self._sanitize_html_tags(parsed)
        # parsed = self._transclude(parsed)
        # parsed = self._extract_custom_tags(parsed)
        # parsed = self._parse(parsed)
        # parsed = self._substitute_custom_tags_placeholders(parsed)
        # parsed = self._substitute_nowiki_placeholders(parsed)
        parsed = wikicode  # FIXME disabled because of infinite loop

        self._metadata = ParsingMetadata(
            links=links,
            categories=categories,
            parse_duration=round((_time.time() * 1000) - start_time),
            parse_date=_utils.now(),
            size_before=size_before,
            size_after=len(parsed.encode('utf-8')),
            template_tag_error=self._template_tag_error,
        )
        return parsed

    def _parse_template_tags(self, wikicode: str) -> str:
        comment_pref_l = len(self.COMMENT_DELIMS[0])
        comment_suff_l = len(self.COMMENT_DELIMS[1])
        expr_insert_pref_l = len(self.EXPR_INSERT_DELIMS[0])
        expr_insert_suff_l = len(self.EXPR_INSERT_DELIMS[1])
        tag_pref_l = len(self.TEMPLATE_TAG_DELIMS[0])
        tag_suff_l = len(self.TEMPLATE_TAG_DELIMS[1])

        i = 0
        code_l = len(wikicode)

        @_dataclasses.dataclass
        class ParseStackElement:
            buffer: str = ''
            current_tag: _tt.TemplateTag = None
            parse_section: bool = True

        tag_delim = None
        tag_buffer = ''
        in_string = False
        str_backslashes = 0
        stack = [ParseStackElement()]

        # TODO add warning if max length is reached
        while not self._template_tag_error and i < code_l and i <= self.MAX_TEXT_LENGTH:
            c = wikicode[i]

            if not in_string and not tag_delim:
                if (stack[-1].parse_section and i < code_l + comment_pref_l
                        and wikicode[i:i + comment_pref_l] == self.COMMENT_DELIMS[0]):
                    tag_delim = self.COMMENT_DELIMS[0]
                    i += comment_pref_l
                elif (stack[-1].parse_section and i < code_l + expr_insert_pref_l
                      and wikicode[i:i + expr_insert_pref_l] == self.EXPR_INSERT_DELIMS[0]):
                    tag_delim = self.EXPR_INSERT_DELIMS[0]
                    i += expr_insert_pref_l
                elif (i < code_l + tag_pref_l
                      and wikicode[i:i + tag_pref_l] == self.TEMPLATE_TAG_DELIMS[0]):
                    tag_delim = self.TEMPLATE_TAG_DELIMS[0]
                    i += tag_pref_l

            elif in_string:
                if c == '\\':
                    str_backslashes += 1
                else:
                    if c == '"' and str_backslashes % 2 == 0:
                        in_string = False
                    str_backslashes = 0
                stack[-1].buffer += c
                i += 1

            elif tag_delim:
                if (stack[-1].parse_section and tag_delim == self.COMMENT_DELIMS[0]
                        and i < code_l + comment_suff_l
                        and wikicode[i:i + comment_suff_l] == self.COMMENT_DELIMS[1]):
                    # Ignore comments’ content
                    tag_buffer = ''
                    i += comment_suff_l

                elif stack[-1].parse_section and tag_delim == self.EXPR_INSERT_DELIMS[0]:
                    if c == '"':
                        in_string = True
                        str_backslashes = 0
                    elif (i < code_l + expr_insert_suff_l
                          and wikicode[i:i + expr_insert_suff_l] == self.EXPR_INSERT_DELIMS[1]):
                        stack[-1].buffer += self._evaluate_expression_inclusion(tag_buffer)
                        tag_buffer = ''
                        i += expr_insert_suff_l

                elif tag_delim == self.TEMPLATE_TAG_DELIMS[0]:
                    if c == '"':
                        in_string = True
                        str_backslashes = 0
                        tag_buffer += c
                        i += 1
                        continue

                    if i + tag_suff_l >= code_l or wikicode[i:i + tag_suff_l] != self.TEMPLATE_TAG_DELIMS[1]:
                        stack[-1].buffer += self._error('Syntax error: Unclosed tag')
                        tag_buffer = ''
                        continue

                    tag_buffer = tag_buffer.strip()
                    if not tag_buffer:
                        stack[-1].buffer += self._error('Syntax error: Missing template tag')
                        continue

                    # Using '*' operator as tag may not have any arguments
                    tag_name, *tag_args = tag_buffer.strip().split(maxsplit=1)
                    end = tag_name.startswith('end_')
                    if end:
                        tag_name = tag_name[4:]

                    if not stack[-1].parse_section and ((t := stack[-1].current_tag) and t.name != tag_name):
                        stack[-1].buffer += tag_delim + tag_buffer + c + self.TEMPLATE_TAG_DELIMS[1]
                        tag_buffer = ''
                        i += tag_suff_l
                        continue

                    if tag_name in self.TEMPLATE_TAGS:
                        # noinspection PyArgumentList
                        template_tag = self.TEMPLATE_TAGS[tag_name]()
                    elif (t := stack[-1].current_tag) and tag_name in t.intermediary_tags:
                        template_tag = t
                    else:
                        stack[-1].buffer += self._error(f'Undefined template tag {tag_name!r}')
                        continue

                    if not end:
                        if tag_args:
                            parsed_args = self._parse_template_tag_parameters(tag_args[0])
                        else:
                            parsed_args = []
                        try:
                            content_or_parse_section = template_tag.evaluate(
                                self._context, parsed_args, tag=tag_name)
                        except RuntimeError as e:
                            self._error(f'Syntax error: {e}')
                        else:
                            if template_tag.is_standalone:
                                stack[-1].buffer += str(content_or_parse_section)
                            else:
                                stack.append(ParseStackElement(
                                    current_tag=template_tag,
                                    parse_section=bool(content_or_parse_section),
                                ))
                        tag_buffer = ''
                        i += tag_suff_l
                    else:
                        if tag_args:
                            self._error('Syntax error: End tags do not take arguments')
                        elif template_tag.is_standalone:
                            self._error(f'Syntax erro: Tag {tag_name!r} should not have a closing tag')
                        elif stack[-1].current_tag != template_tag.name:
                            self._error(f'Syntax error: Stray end tag {"end_" + tag_name!r}')
                        else:
                            top = stack.pop()
                            stack[-1].buffer += template_tag.transform_section(self._context, top.buffer)

                else:
                    tag_buffer += c
                    i += 1

            else:
                stack[-1].buffer += c
                i += 1

        if tag_delim:
            stack[-1].buffer += tag_delim + tag_buffer
        if self._template_tag_error:
            while len(stack) > 1:
                stack[-1].buffer += stack.pop().buffer
            stack[-1].buffer += wikicode[i:]

        return stack[-1].buffer

    def _evaluate_expression_inclusion(self, tag_buffer: str) -> str:
        if not tag_buffer.strip():
            return self._error('Syntax error: Missing expression')
        try:
            expr = self._parse_template_tag_parameters(tag_buffer)
        except ValueError as e:
            return self._error(str(e))
        if (l := len(expr)) != 1:
            return self._error(f'Expecting 1 expression, got {l}')
        return str(expr[0].evaluate()[0])

    def _parse_template_tag_parameters(self, raw_params: str) -> list:
        return []  # TODO

    def _error(self, message: str) -> str:
        if not self._template_tag_error:
            self._template_tag_error = True
        # TODO escape message
        # language=HTML
        return f'<span class="text-danger">{message}</span>'

    def _sanitize_html_tags(self, wikicode: str) -> str:
        """Parse all HTML tags, i.e. remove disallowed attributes and disable disallowed tags."""

        def repl(m: _re.Match[str]) -> str:
            match = m.group(0)
            slash = m.group(1)
            group = m.group(2)
            if group not in self.HTML_TAGS and group not in self.CUSTOM_TAGS:
                return f'&lt;/{group}' if slash else f'&lt;{group}'
            return match

        # TODO remove disallowed attributes
        return _re.sub(r'<(/?)(\w+)', repl, _re.sub(r'<(?=[^\w/])', '&lt;', wikicode))

    def _transclude(self, wikicode: str) -> str:
        """Transclude all templates and other pages."""
        return wikicode  # TODO

    def _extract_custom_tags(self, wikicode: str) -> str:
        """Replace all custom tags by placeholders."""
        return wikicode  # TODO

    def _parse(self, wikicode: str) -> str:
        """Parse the article (links, titles, paragraphs, etc.)."""
        return wikicode  # TODO

    def _substitute_custom_tags_placeholders(self, wikicode: str) -> str:
        """Replace all custom tag placeholders by their associated value."""
        return wikicode  # TODO

    def _substitute_nowiki_placeholders(self, wikicode: str):
        """Replace all nowiki placeholders with their associated value."""
        for placeholder, text in self._context.nowiki_placeholders.items():
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
        return f'@REDIRECT[[{page_title}]]'
