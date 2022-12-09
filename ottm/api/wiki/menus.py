import dataclasses

from . import pages, parser
from .namespaces import *
from ..permissions import *
from ... import page_context as pc, wiki_special_pages as wsp, settings


@dataclasses.dataclass(frozen=True)
class Menu:
    id: str
    title: str
    items: list[str]


def get_menus(page_context: pc.WikiPageContext, menu_id: str) -> list[Menu]:
    if menu_id == 'main':
        return _get_dynamic_menus(page_context)
    else:
        return [_get_builtin_menu(page_context, menu_id)]


def _get_dynamic_menus(page_context: pc.WikiPageContext) -> list[Menu]:
    language = page_context.language
    menu = pages.get_interface_page('SideMenu', render=False)
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
                title = pages.get_interface_page(f'Menu{entry}', language=language, render=False) or entry
    return menus


def _get_menu_item_page_title(page_title: str) -> str:
    match page_title:
        case 'MainPage-url':
            return pages.MAIN_PAGE_TITLE
        case title:
            return title


def _get_menu_item_label(item_label: str, language: settings.UILanguage) -> str | None:
    match item_label:
        case 'MainPage-name':
            return language.translate('wiki.main_page_title')
        case label if item_label.endswith('-name'):
            label = label[:-5]
            if wsp.SPECIAL_PAGES.get(label):
                return None
            return NS_INTERFACE.get_full_page_title(f'MenuItem{label}/{language.code}')
        case label:
            return label


def _get_builtin_menu(page_context: pc.WikiPageContext, menu_id: str) -> Menu:
    user = page_context.user
    page = page_context.page
    language = page_context.language

    items: list[dict[str, str | dict[str | str]]] = []
    match menu_id:
        case 'wiki_tools':
            items.append({'title': 'Special:UploadFile'})
            items.append({'title': 'Special:SpecialPages'})
        case 'page_tools':
            if page.namespace != NS_SPECIAL:
                if page.exists:
                    if user.has_permission(PERM_WIKI_DELETE):
                        items.append({'title': 'Special:DeletePage', 'subpage': page.full_title})
                    if user.has_permission(PERM_WIKI_RENAME):
                        items.append({'title': 'Special:RenamePage', 'subpage': page.full_title})
                if user.has_permission(PERM_WIKI_PROTECT):
                    items.append({'title': 'Special:ProtectPage', 'subpage': page.full_title})
            items.append({'title': 'Special:SubPages', 'subpage': page.full_title + '/'})
        case 'more':
            if page.namespace != NS_SPECIAL:
                items.append({'title': 'Special:LinkedPages', 'subpage': page.full_title})
                if hasattr(page_context, 'revision') and page_context.revision:
                    items.append({'title': page.full_title, 'label': 'permalink',
                                  'args': {'revid': page_context.revision.id}})
                    items.append({'title': page.full_title, 'label': 'page_info', 'args': {'action': 'info'}})
                items.append({'title': 'Special:Logs', 'subpage': page.full_title})
        case 'categories':
            pass  # TODO
        case _:
            raise ValueError(f'invalid menu ID "{menu_id}"')

    return _get_menu_object(language, menu_id, language.translate(f'wiki.menu.side.{menu_id}.title'), items)


def _get_menu_object(language, id_: str, title: str, items: list[dict[str, str | dict[str | str]]]) -> Menu:
    menu_items = []
    for item in items:
        page_title = item['title']
        ns, p_title = pages.split_title(page_title)
        tooltip = None
        access_key = None
        if 'subpage' in item:
            page_title += '/' + item['subpage']
        if not item.get('label') and ns == NS_SPECIAL:
            label = language.translate(f'wiki.special_page.{p_title}.menu.label')
            tooltip = language.translate(f'wiki.special_page.{p_title}.menu.tooltip')
            if sp := wsp.SPECIAL_PAGES.get(p_title):
                access_key = sp.access_key
        elif not item.get('label') and ns == NS_INTERFACE:
            label = pages.get_interface_page(p_title, None, language, render=False)
        else:
            if id_:
                label_ = item['label']
                label = language.translate(f'wiki.menu.side.{id_}.item.{label_}.label')
                tooltip = language.translate(f'wiki.menu.side.{id_}.item.{label_}.tooltip')
            else:
                label = item['label']
        menu_items.append(parser.Parser.format_internal_link(
            page_title,
            language,
            text=label,
            tooltip=tooltip,
            access_key=access_key,
            url_params=item.get('args'),
        ))

    return Menu(id=id_, title=title, items=menu_items)
