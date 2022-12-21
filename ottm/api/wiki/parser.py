"""This module defines the wikicode parser."""
import urllib.parse

import django.shortcuts as dj_scut
from . import namespaces, pages, special_pages
from .constants import *
from ... import settings


class Parser:
    """The wikicode parser."""

    @classmethod
    def format_internal_link(
            cls,
            page_title: str,
            language: settings.UILanguage,
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
        page = pages.get_page(*pages.split_title(page_title))
        page_exists = page.exists and not page.deleted

        link_text = page.full_title if text is None else text

        if current_page_title == page.full_title and not anchor and not url_params:
            return f'<strong class="wiki-recursive-link">{link_text}</strong>' if not only_url else ''

        url = dj_scut.reverse('ottm:wiki_page', kwargs={
            'raw_page_title': pages.url_encode_page_title(page.full_title)
        })
        link_tooltip = tooltip or page.full_title

        if (page_exists or no_red_link
                or url_params.get('action') in (ACTION_TALK, ACTION_INFO, ACTION_HISTORY, ACTION_RAW)):
            params = urllib.parse.urlencode(url_params)
            if params:
                url += '?' + params
            if anchor:
                url += '#' + anchor
        else:
            if page.namespace != namespaces.NS_SPECIAL:
                url += '?action=edit&red_link=1'
            paren = language.translate('wiki.link.red_link.tooltip')
            link_tooltip += f' ({paren})'

        if only_url:
            return url
        return cls.format_link(
            url,
            link_text,
            link_tooltip,
            page_exists,
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
