"""This module defines the subpages special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.forms as _dj_forms

from . import _core
from .. import namespaces as _w_ns, pages as _w_pages
from ... import errors as _errors, permissions as _perms
from .... import forms as _forms, models as _models, page_handlers as _ph, requests as _requests


class ProtectPageSpecialPage(_core.SpecialPage):
    """This special page lets users protect pages.

    Args: ``/<page_name:str>``
        - ``page_name``: the name of the page to protect.
    """

    def __init__(self):
        super().__init__('ProtectPage', _perms.PERM_WIKI_PROTECT, accesskey='p', category=_core.Section.PAGE_OPERATIONS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        target_page = None
        form = _Form()
        global_errors = {form.name: []}
        if params.post:
            form = _Form(params.post)
            if form.is_valid():
                target_page = _w_pages.get_page(*_w_pages.split_title(form.cleaned_data['page_name']))
                protection_level = _models.UserGroup.objects.get(label=form.cleaned_data['protection_level'])
                try:
                    done = _w_pages.protect_page(params.user, target_page, protection_level,
                                                 form.cleaned_data['protect_talks'],
                                                 form.cleaned_data['reason'],
                                                 form.cleaned_data['end_date'])
                except _errors.MissingPermissionError:
                    global_errors[form.name].append('missing_permission')
                else:
                    if done:
                        return _core.Redirect(
                            f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{target_page.full_title}',
                            args={'done': True}
                        )
        else:
            if args:
                target_page = _w_pages.get_page(*_w_pages.split_title('/'.join(args)))
            if target_page:
                block = target_page.get_edit_protection()
                form = _Form(initial={
                    'page_name': target_page.full_title,
                    'protection_level': block and block.protection_level.label,
                    'end_date': block and block.end_date,
                    'protect_talks': block and block.protect_talks,
                })
        if target_page and target_page.exists:
            log_entries = target_page.pageprotectionlog_set.reverse()
        else:
            log_entries = _dj_auth_models.EmptyManager(_models.PageProtectionLog)
        return {
            'title_key': 'title_page' if target_page else 'title',
            'title_value': target_page.full_title if target_page else None,
            'target_page': target_page,
            'form': form,
            'global_errors': global_errors,
            'log_entries': log_entries,
            'done': params.get.get('done'),
        }


class _Form(_ph.WikiForm):
    page_name = _dj_forms.CharField(
        label='page',
        max_length=_models.Page._meta.get_field('title').max_length,
        required=True,
        strip=True,
        validators=[_models.page_title_validator, _forms.non_special_page_validator],
    )
    protection_level = _dj_forms.ChoiceField(
        label='protection_level',
        widget=_dj_forms.Select(attrs={'no_translate': True}),
        required=True,
        choices=(),  # Set in __init__()
        help_text=True,
    )
    end_date = _dj_forms.DateField(
        label='end_date',
        widget=_dj_forms.DateInput(attrs={'type': 'date'}),
        required=False,
        help_text=True,
        validators=[_models.future_date_validator],
    )
    protect_talks = _dj_forms.BooleanField(
        label='protect_talks',
        required=False,
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.UserGroupLog._meta.get_field('reason').max_length,
        required=False,
        strip=True,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('protect_page', False, post=post, initial=initial)
        self.fields['protection_level'].choices = tuple(
            (group.label, group.label) for group in _models.UserGroup.objects.all())
