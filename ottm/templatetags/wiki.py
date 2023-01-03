"""This module defines template tags for the wiki."""
import collections as _coll
import pathlib as _pl
import urllib.parse as _url_parse

import django.core.paginator as _dj_paginator
import django.shortcuts as _dj_scut
import django.template as _dj_template
import django.utils.safestring as _dj_safe

from . import ottm as _ottm
from .. import models, page_handlers as _ph
from ..api import permissions as _perms
from ..api.wiki import constants as _w_cons, menus as _menus, namespaces as _w_ns, pages as _w_pages, parser as _parser

register = _dj_template.Library()

JS_TEMPLATE_FILE = _pl.Path(__file__).parent / 'gadgets-loading-template.min.js'


@register.simple_tag(takes_context=True)
def wiki_inner_link(
        context: _ottm.TemplateContext,
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
    wiki_context: _ph.WikiPageContext = context.get('context')
    current_title = wiki_context.page.full_title if not ignore_current_title else None
    classes = css_classes.split() if css_classes else []
    if url_params:
        params = {k: v for k, v in map(lambda v: v.split('='), url_params.split('&'))}
    else:
        params = {}
    link = _parser.Parser.format_internal_link(
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
    return _dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wiki_page_menu_item(context: _ottm.TemplateContext, action: str) -> str:
    """Render a page menu item.

    :param context: Page context.
    :param action: Menu item’s action.
    :return: The render item.
    """
    wiki_context: _ph.WikiPageContext = context.get('context')
    page_title = wiki_context.page.full_title
    css_classes = ['col-2', 'page-menu-item', 'mdi']
    if action == wiki_context.action:
        css_classes.append('selected')
    if action == _w_cons.ACTION_EDIT:
        if wiki_context.page_exists:
            if wiki_context.can_user_edit:
                text = _ottm.ottm_translate(context, f'wiki.menu.page.edit.label')
                tooltip = _ottm.ottm_translate(context, f'wiki.menu.page.edit.tooltip')
                css_classes.append('mdi-file-document-edit-outline')
            else:
                text = _ottm.ottm_translate(context, f'wiki.menu.page.source.label')
                tooltip = _ottm.ottm_translate(context, f'wiki.menu.page.source.tooltip')
                css_classes.append('mdi-xml')
        else:
            css_classes.append('mdi-file-document-plus-outline')
            text = _ottm.ottm_translate(context, f'wiki.menu.page.create.label')
            tooltip = _ottm.ottm_translate(context, f'wiki.menu.page.create.tooltip')
    else:
        text = _ottm.ottm_translate(context, f'wiki.menu.page.{action}.label')
        tooltip = _ottm.ottm_translate(context, f'wiki.menu.page.{action}.tooltip')
        css_classes.append(
            {
                _w_cons.ACTION_READ: 'mdi-file-document-outline',
                _w_cons.ACTION_TALK: 'mdi-forum-outline',
                _w_cons.ACTION_HISTORY: 'mdi-history',
            }[action]
        )
    access_key = {
        _w_cons.ACTION_READ: 'r',
        _w_cons.ACTION_TALK: 't',
        _w_cons.ACTION_EDIT: 'e',
        _w_cons.ACTION_HISTORY: 'h',
    }[action]
    if action == _w_cons.ACTION_READ:
        params = {}
    else:
        params = {'action': action}
    if action in (_w_cons.ACTION_EDIT, _w_cons.ACTION_READ) and wiki_context.request_params.get.get('revid'):
        params['revid'] = wiki_context.request_params.get.get('revid')
    link = _parser.Parser.format_internal_link(
        page_title,
        wiki_context.language,
        text=text,
        tooltip=tooltip,
        url_params=params,
        css_classes=css_classes,
        access_key=access_key,
    )
    return _dj_safe.mark_safe(link)


@register.simple_tag
def wiki_static(page_title: str) -> str:
    """Return the static resource link for the given wiki page.

    :param page_title: Title of the page to get the static resource from.
    :return: The resource’s link.
    """
    tag = ''
    if page_title == 'gadgets':
        gadgetNames = []  # TODO get from user object
        with JS_TEMPLATE_FILE.open(encoding='utf-8') as f:
            js_code = f.read().replace('"`<PLACEHOLDER>`"', ','.join(repr(g) for g in gadgetNames))
        tag = f'<script>{_w_pages.minify_js(js_code)}</script>'
    else:
        page = _w_pages.get_page(*_w_pages.split_title(page_title))
        if page.exists:
            link = _dj_scut.reverse('ottm:wiki_api')
            title = _url_parse.urlencode({'title': _w_pages.url_encode_page_title(page.full_title)})
            if page.content_type == _w_cons.CT_JS:
                tag = f'<script src="{link}?action=query&query=static&{title}"></script>'
            elif page.content_type == _w_cons.CT_CSS:
                tag = f'<link href="{link}?action=query&query=static&{title}" rel="stylesheet">'
    return _dj_safe.mark_safe(tag)


@register.simple_tag(takes_context=True)
def wiki_diff_link(context: _ottm.TemplateContext, revision: models.PageRevision, against: str) -> str:
    """Render a revision’s diff link.

    :param context: Page context.
    :param revision: Revision to get data from.
    :param against:
    :return: The rendered diff link.
    """
    wiki_context: _ph.WikiPageReadActionContext = context.get('context')
    page = wiki_context.page
    ignore_hidden = not wiki_context.user.has_permission(_perms.PERM_MASK)

    match against:
        case 'previous':
            prev_r = revision.get_previous(ignore_hidden)
            # language=HTML
            text = ('<span class="mdi mdi-arrow-left-thick"></span> '
                    + _ottm.ottm_translate(context, 'wiki.page.read.revision_nav_box.diff_previous'))
            if prev_r:
                link = wiki_inner_link(context, page.full_title, text, url_params=f'revid={prev_r.id}')
                diff = wiki_inner_link(context, page.full_title, '',
                                       url_params=f'oldid={prev_r.id}&newid={revision.id}',
                                       css_classes='mdi mdi-file-compare')
                text = f'{link} ({diff})'
            else:
                # language=HTML
                text = f'{text} (<span class="mdi mdi-file-compare"></span>)'
        case 'current':
            current_r = page.get_latest_revision()
            # language=HTML
            text = ('<span class="mdi mdi-arrow-up-thick"></span> '
                    + _ottm.ottm_translate(context, 'wiki.page.read.revision_nav_box.diff_current'))
            link = wiki_inner_link(context, page.full_title, text, ignore_current_title=True)
            if current_r.id != revision.id:
                diff = wiki_inner_link(context, page.full_title, '',
                                       url_params=f'oldid={revision.id}&newid={current_r.id}',
                                       css_classes='mdi mdi-file-compare')
                text = f'{link} ({diff})'
            else:
                # language=HTML
                text = f'{link} (<span class="mdi mdi-file-compare"></span>)'
        case 'next':
            next_r = revision.get_next(ignore_hidden)
            text = (_ottm.ottm_translate(context, 'wiki.page.read.revision_nav_box.diff_next')
                    # language=HTML
                    + ' <span class="mdi mdi-arrow-right-thick"></span>')
            if next_r:
                link = wiki_inner_link(context, page.full_title, text, url_params=f'revid={next_r.id}')
                diff = wiki_inner_link(context, page.full_title, '',
                                       url_params=f'oldid={revision.id}&newid={next_r.id}',
                                       css_classes='mdi mdi-file-compare')
                text = f'{link} ({diff})'
            else:
                # language=HTML
                text = f'{text} (<span class="mdi mdi-file-compare"></span>)'
        case _:
            raise ValueError(f'invalid value {against}')

    return _dj_safe.mark_safe(text)


@register.simple_tag(takes_context=True)
def wiki_revision_author(context: _ottm.TemplateContext, revision: models.PageRevision) -> str:
    """Format a revision’s author.

    :param context: Page context.
    :param revision: The revision to render the author of.
    :return: The formatted username.
    """
    return _dj_safe.mark_safe(_format_username(context, revision.author))


@register.simple_tag(takes_context=True)
def wiki_revision_comment(context: _ottm.TemplateContext, revision: models.PageRevision) -> str:
    """Format a revision’s comment.

    :param context: Page context.
    :param revision: The revision to render the comment of.
    :return: The formatted comment.
    """
    return _dj_safe.mark_safe(_format_comment(context, revision.comment, revision.comment_hidden))


@register.simple_tag(takes_context=True)
def wiki_page_list(context: _ottm.TemplateContext, pages: _dj_paginator.Paginator, classify: bool = True,
                   paginate: bool = True, no_results_key: str = None) -> str:
    """Render a list of pages.

    :param context: Page context.
    :param pages: A Paginator object containing the pages.
    :param classify: Whether to separate the list based on pages’ first character.
    :param paginate: Whether to add pagination lists.
    :param no_results_key: Translation key for the message displayed when the paginator is empty.
    :return: The rendered list.
    """
    wiki_context: _ph.WikiPageContext = context.get('context')
    if pages.count == 0:
        message = _ottm.ottm_translate(context, no_results_key)
        # language=HTML
        return _dj_safe.mark_safe(f'<div class="alert alert-warning text-center">{message}</div>')
    if paginate:
        pagination = wiki_pagination(context, pages)
    else:
        pagination = ''
    res = f'{pagination}\n<ul>\n'
    for page in pages.get_page(wiki_context.page_index):
        link = wiki_inner_link(context, page.full_title)
        res += f'<li>{link}</li>\n'
    return _dj_safe.mark_safe(res + f'</ul>\n{pagination}')


@register.inclusion_tag('ottm/wiki/tags/revisions_list.html', takes_context=True)
def wiki_revisions_list(context: _ottm.TemplateContext, revisions: _dj_paginator.Paginator, mode: str) \
        -> _ottm.TemplateContext:
    """Render a list of revisions.

    :param context: Page context.
    :param revisions: A Paginator object containing the revisions.
    :param mode: Specifies how the revisions should be rendered. Either 'history' or 'contributions'.
    :return: The rendered revisions list.
    """
    wiki_context: _ph.WikiPageHistoryActionContext | _ph.WikiSpecialPageContext = context.get('context')
    user = wiki_context.user
    ignore_hidden = not user.has_permission(_perms.PERM_MASK)
    Line = _coll.namedtuple(
        'Line',
        ('actions', 'date', 'page_link', 'flags', 'size', 'size_text', 'variation', 'variation_text', 'comment')
    )
    lines = []
    for revision in revisions.get_page(wiki_context.page_index):
        actions = []

        if user.has_permission(_perms.PERM_MASK):
            actions.append(wiki_inner_link(
                context,
                f'Special:MaskRevision/{revision.page.full_title}',
                text='',
                tooltip=_ottm.ottm_translate(context, 'wiki.revisions_list.mask.tooltip'),
                css_classes='mdi mdi-eye-outline wiki-revision-action',
                ignore_current_title=True,
            ))

        if not revision.is_latest(ignore_hidden):
            actions.append(wiki_inner_link(
                context,
                revision.page.full_title,
                text='',
                tooltip=_ottm.ottm_translate(context, 'wiki.revisions_list.current.tooltip'),
                css_classes='mdi mdi-file-arrow-up-down-outline wiki-revision-action',
                url_params=f'oldid={revision.id}&newid={revision.page.get_latest_revision().id}',
                ignore_current_title=True,
            ))
        else:
            # language=HTML
            actions.append(_dj_safe.mark_safe(
                '<span class="mdi mdi-file-arrow-up-down-outline wiki-revision-action"></span>'))

        if previous := revision.get_previous(ignore_hidden):
            actions.append(wiki_inner_link(
                context,
                revision.page.full_title,
                text='',
                tooltip=_ottm.ottm_translate(context, 'wiki.revisions_list.diff.tooltip'),
                css_classes='mdi mdi-file-arrow-left-right-outline wiki-revision-action',
                url_params=f'oldid={previous.id}&newid={revision.id}',
                ignore_current_title=True,
            ))
        else:
            # language=HTML
            actions.append(_dj_safe.mark_safe(
                '<span class="mdi mdi-file-arrow-left-right-outline wiki-revision-action"></span>'))

        is_first = revision.is_first(ignore_hidden)
        if not is_first:
            actions.append(wiki_inner_link(  # TODO URL params
                context,
                revision.page.full_title,
                text='',
                tooltip=_ottm.ottm_translate(context, 'wiki.revisions_list.cancel.tooltip'),
                css_classes='mdi mdi-undo wiki-revision-action',
                ignore_current_title=True,
            ))
        else:
            # language=HTML
            actions.append(_dj_safe.mark_safe('<span class="mdi mdi-undo wiki-revision-action"></span>'))

        if not is_first and user.has_permission(_perms.PERM_WIKI_REVERT):
            actions.append(wiki_inner_link(  # TODO URL params
                context,
                revision.page.full_title,
                text='',
                # TODO number of revisions
                tooltip=_ottm.ottm_translate(context, 'wiki.revisions_list.revert.tooltip', nb=0),
                css_classes='mdi mdi-undo-variant wiki-revision-action',
                ignore_current_title=True,
            ))
        else:
            # language=HTML
            actions.append(_dj_safe.mark_safe('<span class="mdi mdi-undo-variant wiki-revision-action"></span>'))

        match mode:
            case 'history':
                page_link = _format_username(context, revision.author)
            case 'contributions':
                page_link = wiki_inner_link(context, revision.page.full_title, ignore_current_title=True)
            case _:
                raise ValueError(f'invalid revision list mode {mode!r}')

        date = wiki_inner_link(
            context,
            page_title=revision.page.full_title,
            text=_ottm.ottm_format_date(context, revision.date),
            url_params=f'revid={revision.id}',
            ignore_current_title=True,
        )
        flags = []
        if revision.page_creation:
            flags.append((_ottm.ottm_translate(context, 'wiki.revisions_list.flag.creation.label'),
                          _ottm.ottm_translate(context, 'wiki.revisions_list.flag.creation.tooltip'),
                          'success'))
        if revision.is_minor:
            flags.append((_ottm.ottm_translate(context, 'wiki.revisions_list.flag.minor.label'),
                          _ottm.ottm_translate(context, 'wiki.revisions_list.flag.minor.tooltip'),
                          'secondary'))
        if revision.is_bot:
            flags.append((_ottm.ottm_translate(context, 'wiki.revisions_list.flag.bot.label'),
                          _ottm.ottm_translate(context, 'wiki.revisions_list.flag.bot.tooltip'),
                          'light'))
        size = _ottm.ottm_format_number(context, revision.bytes_size, value_only=True)
        size_text = _ottm.ottm_translate(context, 'wiki.revisions_list.size.label', n=size)
        variation = revision.get_byte_size_diff(ignore_hidden=ignore_hidden)
        variation_text = ('+' if variation > 0 else '') + _ottm.ottm_format_number(context, variation, value_only=True)
        comment = _format_comment(context, revision.comment, revision.comment_hidden)

        lines.append(Line(actions, date, page_link, flags, size, size_text, variation, variation_text, comment))
    return {
        'lines': lines,
        'pagination': wiki_pagination(context, revisions),
        'no_results_message': _ottm.ottm_translate(context, 'wiki.revisions_list.no_results_message'),
    }


@register.inclusion_tag('ottm/wiki/tags/topics.html', takes_context=True)
def wiki_render_topics(context: _ottm.TemplateContext, topics: _dj_paginator.Paginator) -> _ottm.TemplateContext:
    """Render a list of revisions.

    :param context: Page context.
    :param topics: A Paginator object containing the topics.
    :return: The rendered topics list.
    """
    return {}  # TODO


@register.simple_tag(takes_context=True)
def wiki_format_log_entry(context: _ottm.TemplateContext, log_entry: models.Log) -> str:
    """Format a log entry.

    :param context: Page context.
    :param log_entry: The log entry to format.
    :return: The formatted log entry.
    """
    if not isinstance(log_entry, models.Log):
        raise TypeError(f'expected instance of {models.Log} class, got {type(log_entry)}')

    formatted_date = _ottm.ottm_format_date(context, log_entry.date)
    match log_entry:
        case models.PageCreationLog(performer=performer, page=page):
            return _ottm.ottm_translate(
                context,
                'wiki.log.page_creation',
                date=formatted_date,
                user=_format_username(context, performer),
                page=wiki_inner_link(context, page.full_title, ignore_current_title=True),
            )
        case models.PageDeletionLog(performer=performer, page=page, reason=reason):
            return _ottm.ottm_translate(
                context,
                'wiki.log.page_deletion',
                date=formatted_date,
                user=_format_username(context, performer),
                page=wiki_inner_link(context, page.full_title, ignore_current_title=True),
                reason=_format_comment(context, reason, False),
            )
        case models.PageProtectionLog(performer=performer, page_namespace_id=ns_id, page_title=title, reason=reason,
                                      end_date=end_date, protection_level=protection_level,
                                      protect_talks=protect_talks):
            page_title = _w_ns.NAMESPACE_IDS[ns_id].get_full_page_title(title)
            if end_date:
                return _ottm.ottm_translate(
                    context,
                    'wiki.log.page_protection',
                    date=formatted_date,
                    user=_format_username(context, performer),
                    page=wiki_inner_link(context, page_title, ignore_current_title=True),
                    group=protection_level.label,
                    until=(_ottm.ottm_format_date(context, end_date)
                           if end_date else _ottm.ottm_translate(context, 'wiki.log.infinite')),
                    talks=str(protect_talks).lower(),
                    reason=_format_comment(context, reason, False),
                )
            return _ottm.ottm_translate(
                context,
                'wiki.log.page_protection_infinite',
                date=formatted_date,
                user=_format_username(context, performer),
                page=wiki_inner_link(context, page_title, ignore_current_title=True),
                group=protection_level.label,
                talks=str(protect_talks).lower(),
                reason=_format_comment(context, reason, False),
            )
        case models.PageRenameLog(performer=performer, old_title=old_title, new_title=new_title, reason=reason,
                                  leave_redirect=leave_redirect):
            if not leave_redirect:
                return _ottm.ottm_translate(
                    context,
                    'wiki.log.page_rename_no_redirect',
                    date=formatted_date,
                    user=_format_username(context, performer),
                    old_title=wiki_inner_link(context, old_title),
                    new_title=wiki_inner_link(context, new_title),
                    reason=_format_comment(context, reason, False),
                )
            return _ottm.ottm_translate(
                context,
                'wiki.log.page_rename',
                date=formatted_date,
                user=_format_username(context, performer),
                old_title=wiki_inner_link(context, old_title),
                new_title=wiki_inner_link(context, new_title),
                reason=_format_comment(context, reason, False),
            )
        case models.PageContentLanguageLog(performer=performer, page=page, language=language, reason=reason):
            return _ottm.ottm_translate(
                context,
                'wiki.log.page_content_language',
                date=formatted_date,
                user=_format_username(context, performer),
                page=wiki_inner_link(context, page.full_title, ignore_current_title=True),
                language_name=language.name,
                language_code=language.code,
                reason=_format_comment(context, reason, False),
            )
        case models.PageContentTypeLog(performer=performer, page=page, content_type=content_type, reason=reason):
            return _ottm.ottm_translate(
                context,
                'wiki.log.page_content_type',
                date=formatted_date,
                user=_format_username(context, performer),
                page=wiki_inner_link(context, page.full_title, ignore_current_title=True),
                content_type=content_type,
                reason=_format_comment(context, reason, False),
            )
        case models.UserAccountCreationLog(user=user):
            return _ottm.ottm_translate(
                context,
                'wiki.log.user_account_creation',
                date=formatted_date,
                user=_format_username(context, user),
            )
        case models.UserRenameLog(performer=performer, old_username=old_name, new_username=new_name, reason=reason):
            return _ottm.ottm_translate(
                context,
                'wiki.log.user_rename',
                date=formatted_date,
                performer=_format_username(context, performer),
                old_name=wiki_inner_link(context, _w_ns.NS_USER.get_full_page_title(old_name), text=old_name,
                                         ignore_current_title=True),
                new_name=wiki_inner_link(context, _w_ns.NS_USER.get_full_page_title(new_name), text=new_name,
                                         ignore_current_title=True),
                reason=_format_comment(context, reason, False),
            )
        case models.UserMaskLog(user=user, performer=performer, reason=reason, masked=masked):
            action = 'masked' if masked else 'unmasked'
            return _ottm.ottm_translate(
                context,
                'wiki.log.user_mask_' + action,
                date=formatted_date,
                performer=_format_username(context, performer),
                user=_format_username(context, user),
                reason=_format_comment(context, reason, False),
            )
        case models.UserGroupLog(user=user, performer=performer, reason=reason, joined=joined, group=group):
            action = 'joined' if joined else 'left'
            if performer:
                return _ottm.ottm_translate(
                    context,
                    'wiki.log.user_group_' + action,
                    date=formatted_date,
                    performer=_format_username(context, performer),
                    user=_format_username(context, user),
                    group=group.label,
                    reason=_format_comment(context, reason, False),
                )
            return _ottm.ottm_translate(
                context,
                'wiki.log.user_group_internal_' + action,
                date=formatted_date,
                user=_format_username(context, user),
                group=group.label,
                reason=_format_comment(context, reason, False),
            )
        case models.UserBlockLog(performer=performer, reason=reason, end_date=end_date, blocked=blocked,
                                 allow_messages_on_own_user_page=allow_messages_on_own_user_page,
                                 user=user, allow_editing_own_settings=allow_editing_own_settings):
            if blocked:
                if end_date:
                    return _ottm.ottm_translate(
                        context,
                        'wiki.log.user_block',
                        date=formatted_date,
                        performer=_format_username(context, performer),
                        user=_format_username(context, user),
                        edit_settings=str(allow_editing_own_settings).lower(),
                        post_messages=str(allow_messages_on_own_user_page).lower(),
                        until=_ottm.ottm_format_date(context, end_date),
                        reason=_format_comment(context, reason, False),
                    )
                return _ottm.ottm_translate(
                    context,
                    'wiki.log.user_block_infinite',
                    date=formatted_date,
                    performer=_format_username(context, performer),
                    user=_format_username(context, user),
                    edit_settings=str(allow_editing_own_settings).lower(),
                    post_messages=str(allow_messages_on_own_user_page).lower(),
                    reason=_format_comment(context, reason, False),
                )
            return _ottm.ottm_translate(
                context,
                'wiki.log.user_unblock',
                date=formatted_date,
                performer=_format_username(context, performer),
                user=_format_username(context, user),
                reason=_format_comment(context, reason, False),
            )
        case models.IPBlockLog(performer=performer, reason=reason, end_date=end_date,
                               allow_messages_on_own_user_page=allow_messages_on_own_user_page,
                               ip=ip, allow_account_creation=allow_account_creation):
            return _ottm.ottm_translate(
                context,
                'wiki.log.ip_block',
                date=formatted_date,
                performer=_format_username(context, performer),
                user=wiki_inner_link(context, _w_ns.NS_USER.get_full_page_title(ip), ignore_current_title=True),
                create_accounts=str(allow_account_creation).lower(),
                post_messages=str(allow_messages_on_own_user_page).lower(),
                until=(_ottm.ottm_format_date(context, end_date)
                       if end_date else _ottm.ottm_translate(context, 'wiki.log.infinite')),
                reason=_format_comment(context, reason, False),
            )


@register.inclusion_tag('ottm/wiki/tags/side_menu.html', takes_context=True)
def wiki_side_menu(context: _ottm.TemplateContext, menu_id: str) -> _ottm.TemplateContext:
    """Format the menu with the given ID.

    :param context: Page context.
    :param menu_id: Menu’s ID.
    :return: The formatted menu.
    """
    wiki_context: _ph.WikiPageContext = context.get('context')
    return {'menus': _menus.get_menus(wiki_context, menu_id)}


@register.simple_tag(takes_context=True)
def wiki_pagination(context: _ottm.TemplateContext, paginator: _dj_paginator.Paginator) -> str:
    """Render a the pagination list for the given paginator object.

    :param context: Page context.
    :param paginator: The paginator object.
    :return: The rendered pagination list.
    """
    wiki_context: _ph.WikiPageContext = context.get('context')
    # noinspection PyUnresolvedReferences
    page_index = wiki_context.page_index
    items = []
    for index in paginator.get_elided_page_range(page_index, on_each_side=2):
        if isinstance(index, int):
            url = wiki_add_url_params(context, page=index)
            tooltip = _ottm.ottm_translate(context, 'wiki.pagination.page.tooltip', page=index)
            active = 'active' if index == page_index else ''
            # noinspection HtmlUnknownTarget
            # language=HTML
            items.append(
                f'<li class="page-item {active}" title="{tooltip}"><a class="page-link" href="{url}">{index}</a></li>')
        else:
            # language=HTML
            items.append(f'<li class="page-item disabled"><a class="page-link" href="#">{index}</a></li>')

    # language=HTML
    nav = '<nav><ul class="pagination justify-content-center">' + ''.join(items) + '</ul></nav>'
    numbers = []
    for nb in [20, 50, 100, 200, 500]:
        url = wiki_add_url_params(context, results_per_page=nb)
        tooltip = _ottm.ottm_translate(context, 'wiki.pagination.per_page_item.tooltip', nb=nb)
        active = 'active' if nb == paginator.per_page else ''
        # noinspection HtmlUnknownTarget
        # language=HTML
        numbers.append(
            f'<li class="page-item {active}" title="{tooltip}"><a class="page-link" href="{url}">{nb}</a></li>')
    number_per_page_list = '<ul class="pagination justify-content-center">' + ''.join(numbers) + '</ul>'
    return _dj_safe.mark_safe(nav + number_per_page_list)


@register.simple_tag(takes_context=True)
def wiki_add_url_params(context: _ottm.TemplateContext, **kwargs) -> str:
    """Return the current URL with the specified parameters added to it.

    :param context: Page context.
    :param kwargs: Parameters to add to the URL.
    :return: The new URL.
    """
    wiki_context: _ph.WikiPageContext = context.get('context')
    request = wiki_context.request_params.request
    url_path = request.path
    get_params = {k: v for k, v in request.GET.items()}
    get_params.update(kwargs)
    url_params = _url_parse.urlencode(get_params)
    return url_path + ('?' + url_params if url_params else '')


def _format_username(context: _ottm.TemplateContext, user: models.CustomUser) -> str:
    wiki_context: _ph.WikiPageContext = context.get('context')
    can_view = wiki_context.user.has_permission(_perms.PERM_MASK)
    css_classes = ''
    if user.hide_username:
        if not can_view:
            return f'<span class="masked">{_ottm.ottm_translate(context, "wiki.username_hidden")}</span>'
        css_classes = 'masked'
    return wiki_inner_link(context, _w_ns.NS_USER.get_full_page_title(user.username),
                           text=user.username, ignore_current_title=True, css_classes=css_classes)


def _format_comment(context: _ottm.TemplateContext, comment: str, hide: bool) -> str:
    # TODO parse comment
    wiki_context: _ph.WikiPageContext = context.get('context')
    can_view = wiki_context.user.has_permission(_perms.PERM_MASK)
    css_classes = ''
    if hide:
        if not can_view:
            return f'<span class="masked">{_ottm.ottm_translate(context, "wiki.comment_hidden")}</span>'
        css_classes = 'masked'
    return f'<span class="font-italic {css_classes}">({comment})</span>' if comment else ''
