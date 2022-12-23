"""This module defines the special page to edit a user’s follow list."""
import typing as _typ

import django.forms as _dj_forms

from . import _core
from .. import namespaces as _w_ns, pages as _w_pages
from ... import utils as _utils, errors as _errors
from .... import models as _models, page_handlers as _ph, requests as _requests, settings as _settings


class EditFollowListSpecialPage(_core.SpecialPage):
    """This special page lets users edit their follow list.

    Args:

    - ``/raw``
        - edit the follow list manually.
    - ``/clear``
        - clear the follow list
    """

    def __init__(self):
        super().__init__('EditFollowList', category=_core.Section.USERS, has_custom_css=True)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        if not params.user.is_authenticated:
            return _core.Redirect(_w_ns.NS_USER.get_full_page_title(params.user.username))
        match args:
            case ['clear', *_]:
                action = 'clear'
            case ['raw', *_]:
                action = 'edit_raw'
            case _:
                action = 'edit'
        global_errors = {}
        if action != 'clear':
            if params.post:
                if action == 'edit_raw':
                    form = _RawEditForm(post=params.post)
                    global_errors[form.name] = []
                    if form.is_valid():
                        pages = [_w_pages.get_page(*_w_pages.split_title(t))
                                 for t in _utils.normalize_line_returns(form.cleaned_data['page_names']).split('\n')]
                        try:
                            _w_pages.update_follow_list(params.user, *pages)
                        except _errors.FollowSpecialPageError:
                            global_errors[form.name].append('follow_special_page')
                        else:
                            return _core.Redirect(
                                f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/raw',
                                args={'done': True}
                            )
                else:
                    form = _EditForm(params.user, params.ui_language, post=params.post)
                    if form.is_valid():
                        for t in form.cleaned_data['page_names']:
                            _w_pages.unfollow_page(params.user, _w_pages.get_page(*_w_pages.split_title(t)))
                        else:
                            return _core.Redirect(
                                f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}',
                                args={'done': True}
                            )
            else:
                pages = [p.full_title for p in params.user.get_followed_pages()]
                if action == 'edit_raw':
                    form = _RawEditForm(initial={'page_names': '\n'.join(pages)})
                else:
                    form = _EditForm(params.user, params.ui_language, initial={'pages': pages})
        else:
            if params.post:
                _w_pages.clear_follow_list(params.user)
                return _core.Redirect(_w_ns.NS_SPECIAL.get_full_page_title(self.name), args={'done': True})
            else:
                form = _ClearForm()
        return {
            'title_key': 'title_clear' if action == 'clear' else 'title',
            'form': form,
            'global_errors': global_errors,
            'done': params.get.get('done'),
        }


class _RawEditForm(_ph.WikiForm):
    page_names = _dj_forms.CharField(
        label='page_names',
        widget=_dj_forms.Textarea(attrs={'rows': 20}),
        required=False,
        strip=True,
        help_text=True,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('edit_raw', False, post=post, initial=initial)


class _EditForm(_ph.WikiForm):
    page_names = _dj_forms.MultipleChoiceField(
        label='pages',
        widget=_dj_forms.CheckboxSelectMultiple(attrs={'no_translate': True}),
        choices=(),
        required=False,
    )

    def __init__(self, user: _models.User, language: _settings.UILanguage, post=None, initial=None):
        super().__init__('edit', False, post=post, initial=initial)
        pages = []
        ns_name = None
        buffer = []
        for page in user.get_followed_pages():
            if ns_name != (name := page.namespace.get_display_name(language)):
                if buffer:
                    pages.append((ns_name, tuple(buffer)))
                    buffer.clear()
                ns_name = name
            buffer.append((page.full_title, page.full_title))
        if buffer:
            pages.append((ns_name, tuple(buffer)))
        # FIXME find a way to display optgroup names in form
        self.fields['page_names'].choices = tuple(pages)


class _ClearForm(_ph.WikiForm):
    def __init__(self):
        super().__init__('clear', False, danger=True)
