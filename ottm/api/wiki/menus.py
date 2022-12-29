"""This module defines functions to generate the wiki’s side menus."""
import dataclasses as _dc
import urllib.parse as _url_parse

from . import constants as _w_cons, namespaces as _w_ns, pages as _w_pages, parser as _parser, special_pages as _w_sp
from .. import auth as _auth, data_types as _data_types, permissions as _perms
from ... import page_handlers as _ph, settings as _settings


@_dc.dataclass(frozen=True)
class Menu:
    id: str
    title: str
    items: list[str]


def get_menus(page_context: _ph.WikiPageContext, menu_id: str) -> list[Menu]:
    if menu_id == 'main':
        return _get_dynamic_menus(page_context)
    else:
        return [_get_builtin_menu(page_context, menu_id)]


def _get_dynamic_menus(page_context: _ph.WikiPageContext) -> list[Menu]:
    language = page_context.language
    menu = _w_pages.get_interface_page('SideMenu', rendered=False)
    menus = []
    title = None
    items = []
    for line in menu.split('\n'):
        if line.startswith('*'):
            if line.startswith('**'):
                entry = line[2:]
                if '|' in entry:
                    page_title, label = line[2:].split('|', maxsplit=1)
                    items.append({
                        'title': _get_menu_item_page_title(page_title.strip()),
                        'label': _get_menu_item_label(label.strip(), language),
                    })
            else:
                if title is not None:
                    menus.append(_get_menu_object(language, '', title, items))
                    items = []
                entry = line[1:].strip()
                title = _w_pages.get_interface_page(f'Menu{entry}', language=language, rendered=False) or entry
    return menus


def _get_menu_item_page_title(page_title: str) -> str:
    match page_title:
        case 'MainPage-url':
            return _w_pages.MAIN_PAGE_TITLE
        case title:
            return title


def _get_menu_item_label(item_label: str, language: _settings.UILanguage) -> str | None:
    match item_label:
        case 'MainPage-name':
            return language.translate('wiki.main_page_title')
        case label if item_label.endswith('-name'):
            label = label[:-5]
            if _w_sp.SPECIAL_PAGES.get(label):
                return None
            return _w_ns.NS_INTERFACE.get_full_page_title(f'MenuItem{label}/{language.code}')
        case label:
            return label


def _get_builtin_menu(page_context: _ph.WikiPageContext, menu_id: str) -> Menu:
    user = page_context.user
    page = page_context.page
    language = page_context.language

    items: list[dict[str, str | dict[str | str]]] = []
    match menu_id:
        case 'wiki_tools':
            items.append({'title': 'Special:UploadFile'})
            items.append({'title': 'Special:SpecialPages'})

        case 'page_tools':
            if page.namespace != _w_ns.NS_SPECIAL:
                if page.exists:
                    if user.has_permission(_perms.PERM_WIKI_DELETE):
                        items.append({'title': 'Special:DeletePage', 'subpage': page.full_title})
                    if user.has_permission(_perms.PERM_WIKI_RENAME):
                        items.append({'title': 'Special:RenamePage', 'subpage': page.full_title})
                if user.has_permission(_perms.PERM_WIKI_PROTECT):
                    items.append({'title': 'Special:ProtectPage', 'subpage': page.full_title})
            elif _w_sp.SPECIAL_PAGES.get(page.base_name):
                items.append({'title': _w_ns.NS_SPECIAL.get_full_page_title(page.base_name), 'label': 'special_page'})
            if page.namespace == _w_ns.NS_USER and _auth.get_user_from_name(page.base_name):
                username = page.base_name
                target_user = _auth.get_user_from_name(username)
                items.append({'url': f'/user/{username}', 'label': 'user_profile', 'gender': target_user.gender})
                items.append({'title': 'Special:Contributions', 'subpage': username, 'gender': target_user.gender})
                if target_user and user.can_send_emails_to(target_user):
                    items.append({'title': 'Special:SendEmail', 'subpage': username, 'gender': target_user.gender})
                items.append({'title': 'Special:Mute', 'subpage': username, 'gender': target_user.gender})
            if page.namespace != _w_ns.NS_SPECIAL:
                items.append({'title': 'Special:Subpages', 'subpage': page.full_title})
            elif hasattr(page_context, 'target_user') and page_context.target_user:
                items.append({'title': f'User:{page_context.target_user.username}', 'label': 'user_page',
                              'gender': page_context.target_user.gender})
            elif hasattr(page_context, 'target_page') and page_context.target_page:
                items.append({'title': page_context.target_page.full_title, 'label': 'page'})

        case 'more':
            if page.namespace != _w_ns.NS_SPECIAL:
                items.append({'title': 'Special:LinkedPages', 'subpage': page.full_title})
                if (hasattr(page_context, 'revision') and page_context.revision
                        and page_context.action == _w_cons.ACTION_READ):
                    items.append({'title': page.full_title, 'label': 'permalink',
                                  'args': {'revid': page_context.revision.id}})
                if page_context.page_exists:
                    items.append({'title': page.full_title, 'label': 'page_info', 'args': {'action': 'info'}})
                items.append({'title': 'Special:Logs', 'subpage': page.full_title})

        case 'categories':
            pass  # TODO

        case _:
            raise ValueError(f'invalid menu ID "{menu_id}"')

    return _get_menu_object(language, menu_id, language.translate(f'wiki.menu.side.{menu_id}.title'), items)


def _get_menu_object(language: _settings.UILanguage, id_: str, title: str,
                     items: list[dict[str, str | dict[str | str] | _data_types.UserGender]]) -> Menu:
    menu_items = []
    for item in items:
        tooltip = ''
        access_key = None
        if 'gender' in item:
            gender = item['gender']
        else:
            gender = None
        if 'title' in item:
            page_title = item['title']
            ns, p_title = _w_pages.split_title(page_title)
            if 'subpage' in item:
                page_title += '/' + item['subpage']
            if not item.get('label') and ns == _w_ns.NS_SPECIAL:
                label = language.translate(f'wiki.special_page.{p_title}.menu.label', gender=gender)
                tooltip = language.translate(f'wiki.special_page.{p_title}.menu.tooltip', gender=gender)
                if sp := _w_sp.SPECIAL_PAGES.get(p_title):
                    access_key = sp.access_key
            elif not item.get('label') and ns == _w_ns.NS_INTERFACE:
                label = _w_pages.get_interface_page(p_title, language, rendered=False)
            else:
                if id_:
                    label_ = item['label']
                    label = language.translate(f'wiki.menu.side.{id_}.item.{label_}.label', gender=gender)
                    tooltip = language.translate(f'wiki.menu.side.{id_}.item.{label_}.tooltip', gender=gender)
                else:
                    label = item['label']
            menu_items.append(_parser.Parser.format_internal_link(
                page_title,
                language,
                text=label,
                tooltip=tooltip,
                access_key=access_key,
                url_params=item.get('args'),
            ))
        else:
            if id_:
                label_ = item['label']
                label = language.translate(f'wiki.menu.side.{id_}.item.{label_}.label', gender=gender)
                tooltip = language.translate(f'wiki.menu.side.{id_}.item.{label_}.tooltip', gender=gender)
            else:
                label = item['label']
            url = item['url']
            if 'args' in item:
                url += '?' + _url_parse.urlencode(item['args'])
            menu_items.append(_parser.Parser.format_link(
                url,
                label,
                tooltip,
                page_exists=True,
                css_classes=[],
            ))

    return Menu(id=id_, title=title, items=menu_items)
