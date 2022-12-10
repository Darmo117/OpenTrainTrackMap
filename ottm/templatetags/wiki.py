"""This module defines template tags for the wiki."""
import collections
import typing as typ

import django.core.paginator as dj_paginator
import django.template as dj_template
import django.utils.safestring as dj_safe

from .ottm import *
from .. import models, page_context
from ..api.permissions import *
from ..api.wiki import constants as w_cons, menus, pages as w_pages, parser, namespaces as w_ns

register = dj_template.Library()


@register.filter
def wiki_url_escape(value: str) -> str:
    """Convert the given page name to a URL-safe value."""
    return dj_safe.mark_safe(w_pages.url_encode_page_title(value))


@register.simple_tag(takes_context=True)
def wiki_translate(context: dict[str, typ.Any], key: str, **kwargs) -> str:
    """Translate the given key. The prefix 'wiki.' is appended automatically.

    :param context: Page context.
    :param key: Key to translate.
    :param kwargs: Translation’s arguments.
    :return: The translated text or the key in it is undefined for the current language.
    """
    return ottm_translate(context, 'wiki.' + key, **kwargs)


@register.simple_tag(takes_context=True)
def wiki_inner_link(
        context: dict[str, typ.Any],
        page_title: str,
        text: str = None,
        tooltip: str = None,
        anchor: str = None,
        url_params: str = None,
        css_classes: str = None,
        access_key: str = None,
        ignore_current_title: bool = False,
        no_red_link: bool = False,
        only_url: bool = False,
        new_tab: bool = False,
) -> str:
    """Render an internal link.

    :param context: Page context.
    :param page_title: Title of the page to link.
    :param text: Link’s text. May be None.
    :param tooltip: Link’s tooltip.
    :param anchor: Link’s anchor.
    :param url_params: Additional URL parameters.
    :param css_classes: Additional CSS classes.
    :param access_key: Link’s access key.
    :param ignore_current_title: Whether to ignore the current page’s title when rendering the link.
    :param no_red_link: Whether to keep the link the default color even if the target page does not exist.
    :param only_url: Whether to return the URL instead of rendering it.
    :param new_tab: Whether to add target="_blank" to link’s tag.
    :return: The rendered link.
    """
    wiki_context: page_context.WikiPageContext = context.get('context')
    current_title = wiki_context.page.full_title if not ignore_current_title else None
    classes = css_classes.split() if css_classes else []
    if url_params:
        params = {k: v for k, v in map(lambda v: v.split('='), url_params.split('&'))}
    else:
        params = {}
    link = parser.Parser.format_internal_link(
        page_title,
        wiki_context.language,
        text=text,
        tooltip=tooltip,
        anchor=anchor,
        url_params=params,
        css_classes=classes,
        access_key=access_key,
        current_page_title=current_title,
        no_red_link=no_red_link,
        only_url=only_url,
        open_in_new_tab=new_tab,
    )
    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wiki_page_menu_item(context: dict[str, typ.Any], action: str) -> str:
    """Render a page menu item.

    :param context: Page context.
    :param action: Menu item’s action.
    :return: The render item.
    """
    wiki_context: page_context.WikiPageContext = context.get('context')
    page_title = wiki_context.page.full_title
    css_classes = ['col-2', 'page-menu-item', 'mdi']
    if action == wiki_context.action:
        css_classes.append('selected')
    if action == w_cons.ACTION_EDIT:
        if wiki_context.page_exists:
            if wiki_context.can_user_edit:
                text = wiki_translate(context, f'menu.page.edit.label')
                tooltip = wiki_translate(context, f'menu.page.edit.tooltip')
                css_classes.append('mdi-file-document-edit-outline')
            else:
                text = wiki_translate(context, f'menu.page.source.label')
                tooltip = wiki_translate(context, f'menu.page.source.tooltip')
                css_classes.append('mdi-xml')
        else:
            css_classes.append('mdi-file-document-plus-outline')
            text = wiki_translate(context, f'menu.page.create.label')
            tooltip = wiki_translate(context, f'menu.page.create.tooltip')
    else:
        text = wiki_translate(context, f'menu.page.{action}.label')
        tooltip = wiki_translate(context, f'menu.page.{action}.tooltip')
        css_classes.append(
            {
                w_cons.ACTION_READ: 'mdi-file-document-outline',
                w_cons.ACTION_TALK: 'mdi-forum-outline',
                w_cons.ACTION_HISTORY: 'mdi-history',
            }[action]
        )
    access_key = {
        w_cons.ACTION_READ: 'r',
        w_cons.ACTION_TALK: 't',
        w_cons.ACTION_EDIT: 'e',
        w_cons.ACTION_HISTORY: 'h',
    }[action]
    if action == w_cons.ACTION_READ:
        params = {}
    else:
        params = {'action': action}
    link = parser.Parser.format_internal_link(
        page_title,
        wiki_context.language,
        text=text,
        tooltip=tooltip,
        url_params=params,
        css_classes=css_classes,
        access_key=access_key,
    )
    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wiki_static(context: dict[str, typ.Any], page_title: str) -> str:
    """Return the static resource link for the given wiki page.

    :param context: Page context.
    :param page_title: Title of the page to get the static resource from.
    :return: The resource’s link.
    """
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_diff_link(context: dict[str, typ.Any], revision: models.PageRevision, against: str,
                   show_nav_link: bool = True) -> str:
    """Render a revision’s diff link.

    :param context: Page context.
    :param revision: Revision to get data from.
    :param against:
    :param show_nav_link:
    :return: The rendered diff link.
    """
    match against:
        case 'previous':
            pass
        case 'current':
            pass
        case 'next':
            pass
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_revision_comment(context: dict[str, typ.Any], revision: models.PageRevision) -> str:
    """Format a revision’s comment.

    :param context: Page context.
    :param revision: The revision to render the comment of.
    :return: The formatted comment.
    """
    return ''  # TODO


@register.simple_tag(takes_context=True)
def wiki_page_list(context: dict[str, typ.Any], pages: dj_paginator.Paginator, paginate: bool = True) -> str:
    """Render a list of pages.

    :param context: Page context.
    :param pages: A Paginator object containing the pages.
    :param paginate: Whether to add pagination buttons.
    :return: The rendered list.
    """
    return ''  # TODO


@register.inclusion_tag('ottm/wiki/tags/revisions_list.html', takes_context=True)
def wiki_revisions_list(context: dict[str, typ.Any], revisions: dj_paginator.Paginator, mode: str) \
        -> dict[str, typ.Any]:
    """Render a list of revisions.

    :param context: Page context.
    :param revisions: A Paginator object containing the revisions.
    :param mode: Specifies how the revisions should be rendered. Either 'history' or 'contributions'.
    :return: The rendered revisions list.
    """
    wiki_context: page_context.WikiPageHistoryActionContext | page_context.WikiSpecialPageContext = \
        context.get('context')
    user = wiki_context.user
    ignore_hidden = not user.has_permission(PERM_WIKI_MASK)
    Line = collections.namedtuple(
        'Line', ('actions', 'date', 'page_link', 'flags', 'size', 'size_text', 'variation', 'comment'))
    lines = []
    for revision in revisions.get_page(wiki_context.page_index):
        actions = []
        if user.has_permission(PERM_WIKI_MASK):
            actions.append(wiki_inner_link(
                context,
                f'Special:Mask/{revision.page.full_title}',
                text='',
                tooltip=wiki_translate(context, 'revisions_list.mask.tooltip'),
                css_classes='mdi mdi-eye-outline wiki-revision-action',
                ignore_current_title=True,
            ))
        if not revision.is_latest(ignore_hidden):
            actions.append(wiki_inner_link(
                context,
                revision.page.full_title,
                text='',
                tooltip=wiki_translate(context, 'revisions_list.current.tooltip'),
                css_classes='mdi mdi-file-arrow-up-down-outline wiki-revision-action',
                url_params=f'revid={revision.id}&diff=current',
                ignore_current_title=True,
            ))
        else:
            actions.append(dj_safe.mark_safe(
                '<span class="mdi mdi-file-arrow-up-down-outline wiki-revision-action"></span>'))
        if previous := revision.get_previous(ignore_hidden):
            actions.append(wiki_inner_link(
                context,
                revision.page.full_title,
                text='',
                tooltip=wiki_translate(context, 'revisions_list.diff.tooltip'),
                css_classes='mdi mdi-file-arrow-left-right-outline wiki-revision-action',
                url_params=f'revid={previous.id}&diff=current',
                ignore_current_title=True,
            ))
        else:
            actions.append(dj_safe.mark_safe(
                '<span class="mdi mdi-file-arrow-left-right-outline wiki-revision-action"></span>'))
        is_first = revision.is_first(ignore_hidden)
        if not is_first:
            actions.append(wiki_inner_link(
                context,
                revision.page.full_title,
                text='',
                tooltip=wiki_translate(context, 'revisions_list.cancel.tooltip'),
                css_classes='mdi mdi-undo wiki-revision-action',
                ignore_current_title=True,
            ))
        else:
            actions.append(dj_safe.mark_safe(
                '<span class="mdi mdi-undo wiki-revision-action"></span>'))
        if not is_first and user.has_permission(PERM_WIKI_REVERT):
            actions.append(wiki_inner_link(
                context,
                revision.page.full_title,
                text='',
                tooltip=wiki_translate(context, 'revisions_list.revert.tooltip', nb=0),  # TODO
                css_classes='mdi mdi-undo-variant wiki-revision-action',
                ignore_current_title=True,
            ))

        match mode:
            case 'history':
                page_link = _format_username(context, revision.author)
            case 'contributions':
                page_link = wiki_inner_link(context, revision.page.full_title, ignore_current_title=True)
            case _:
                raise ValueError(f'invalid revision list mode {mode!r}')

        date = ottm_format_date(context, revision.date)
        flags = []
        if revision.is_minor:
            flags.append((wiki_translate(context, 'revisions_list.flag.minor.label'),
                          wiki_translate(context, 'revisions_list.flag.minor.tooltip')))
        if revision.is_bot:
            flags.append((wiki_translate(context, 'revisions_list.flag.bot.label'),
                          wiki_translate(context, 'revisions_list.flag.bot.tooltip')))
        variation = revision.get_byte_size_diff(ignore_hidden=ignore_hidden)
        size = revision.bytes_size
        size_text = wiki_translate(context, 'revisions_list.size.label', n=size)
        comment = _format_comment(context, revision.comment, revision.comment_hidden)

        lines.append(Line(actions, date, page_link, flags, size, size_text, variation, comment))
    return {
        'lines': lines,
    }


@register.inclusion_tag('ottm/wiki/tags/topics.html', takes_context=True)
def wiki_render_topics(context: dict[str, typ.Any], topics: dj_paginator.Paginator) -> dict[str, typ.Any]:
    """Render a list of revisions.

    :param context: Page context.
    :param topics: A Paginator object containing the topics.
    :return: The rendered topics list.
    """
    return {}  # TODO


@register.simple_tag(takes_context=True)
def wiki_format_log_entry(context: dict[str, typ.Any], log_entry: models.Log) -> str:
    """Format a log entry.

    :param context: Page context.
    :param log_entry: The log entry to format.
    :return: The formatted log entry.
    """
    if not isinstance(log_entry, models.Log):
        raise TypeError(f'expected instance of {models.Log} class, got {type(log_entry)}')

    formatted_date = ottm_format_date(context, log_entry.date)
    match log_entry:
        case models.PageCreationLog(performer=performer, page=page):
            return wiki_translate(
                context,
                'log.page_creation',
                date=formatted_date,
                user=_format_username(context, performer),
                page=wiki_inner_link(context, page.full_title, ignore_current_title=True),
            )
        case models.PageDeletionLog(performer=performer, page=page, reason=reason):
            return wiki_translate(
                context,
                'log.page_creation',
                date=formatted_date,
                user=_format_username(context, performer),
                page=wiki_inner_link(context, page.full_title, ignore_current_title=True),
                reason=_format_comment(context, reason, False),
            )
        case models.PageProtectionLog(performer=performer, page=page, reason=reason, end_date=end_date,
                                      protection_level=protection_level):
            return wiki_translate(
                context,
                'log.page_protection',
                date=formatted_date,
                user=_format_username(context, performer),
                page=wiki_inner_link(context, page.full_title, ignore_current_title=True),
                group=protection_level.label,
                until=ottm_format_date(context, end_date) if end_date else wiki_translate(context, 'log.infinite'),
                reason=_format_comment(context, reason, False),
            )
        case models.UserAccountCreationLog(user=user):
            return wiki_translate(
                context,
                'log.user_account_creation',
                date=formatted_date,
                user=_format_username(context, user),
            )
        case models.UserBlockLog(performer=performer, reason=reason, end_date=end_date,
                                 allow_messages_on_own_user_page=allow_messages_on_own_user_page,
                                 user=user, allow_editing_own_settings=allow_editing_own_settings):
            return wiki_translate(
                context,
                'log.user_block',
                date=formatted_date,
                performer=_format_username(context, performer),
                user=_format_username(context, user),
                edit_settings=str(allow_editing_own_settings).lower(),
                post_messages=str(allow_messages_on_own_user_page).lower(),
                until=ottm_format_date(context, end_date) if end_date else wiki_translate(context, 'log.infinite'),
                reason=_format_comment(context, reason, False),
            )
        case models.IPBlockLog(performer=performer, reason=reason, end_date=end_date,
                               allow_messages_on_own_user_page=allow_messages_on_own_user_page,
                               ip=ip, allow_account_creation=allow_account_creation):
            return wiki_translate(
                context,
                'log.ip_block',
                date=formatted_date,
                performer=_format_username(context, performer),
                user=wiki_inner_link(context, w_ns.NS_USER.get_full_page_title(ip), ignore_current_title=True),
                create_accounts=str(allow_account_creation).lower(),
                post_messages=str(allow_messages_on_own_user_page).lower(),
                until=ottm_format_date(context, end_date) if end_date else wiki_translate(context, 'log.infinite'),
                reason=_format_comment(context, reason, False),
            )


@register.inclusion_tag('ottm/wiki/tags/side_menu.html', takes_context=True)
def wiki_side_menu(context: dict[str, typ.Any], menu_id: str) -> dict[str, typ.Any]:
    """Format the menu with the given ID.

    :param context: Page context.
    :param menu_id: Menu’s ID.
    :return: The formatted menu.
    """
    wiki_context: page_context.WikiPageContext = context.get('context')
    return {'menus': menus.get_menus(wiki_context, menu_id), 'dark_mode': wiki_context.dark_mode}


def _format_username(context: dict[str, typ.Any], user: models.CustomUser) -> str:
    if user.hide_username:
        return f'<span class="wiki-hidden">{wiki_translate(context, "username_hidden")}</span>'
    else:
        return wiki_inner_link(context, w_ns.NS_USER.get_full_page_title(user.username),
                               ignore_current_title=True)


def _format_comment(context: dict[str, typ.Any], comment: str, hide: bool) -> str:
    if hide:
        return f'<span class="wiki-hidden">{wiki_translate(context, "comment_hidden")}</span>'
    else:
        return f'<span class="font-italic">({comment})</span>' if comment else ''
