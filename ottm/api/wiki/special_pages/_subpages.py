"""This module defines the subpages special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.core.paginator as _dj_paginator
import django.forms as _dj_forms

from . import _core
from .. import namespaces as _w_ns, pages as _w_pages
from .... import forms as _forms, models as _models, page_handlers as _ph, requests as _requests


class SubpagesSpecialPage(_core.SpecialPage):
    """This special page lists all subpages of a specific page.

    Args: ``/<page_name:str>``
        - ``page_name``: the name of the page to list subpages of.
    """

    def __init__(self):
        super().__init__('Subpages', accesskey='u', category=_core.Section.PAGE_LISTS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        form = _Form()
        target_page = None
        subpages = _dj_auth_models.EmptyManager(_models.PageRevision)
        if title := '/'.join(args):
            target_page = _w_pages.get_page(*_w_pages.split_title(title))
            subpages = target_page.get_subpages()
        if params.POST:
            form = _Form(params.POST)
            if form.is_valid():
                return _core.Redirect(
                    f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{form.cleaned_data["page_name"]}')
        else:
            if target_page:
                form = _Form(initial={'page_name': target_page.full_title})
        paginator = _dj_paginator.Paginator(subpages, params.results_per_page)
        return {
            'title_key': 'title_page' if target_page else 'title',
            'title_value': target_page.full_title if target_page else None,
            'target_page': target_page,
            'subpages': paginator,
            'form': form,
            'max_page_index': paginator.num_pages,
        }


class _Form(_ph.WikiForm):
    page_name = _dj_forms.CharField(
        label='page',
        max_length=_models.Page._meta.get_field('title').max_length,
        required=True,
        strip=True,
        validators=[_models.page_title_validator, _forms.non_special_page_validator, _forms.page_exists_validator],
    )

    def __init__(self, post=None, initial=None):
        super().__init__('select_page', False, post=post, initial=initial)
