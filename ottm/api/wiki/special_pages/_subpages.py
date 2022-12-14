"""This module defines the subpages special page."""
import typing as _typ

import django.contrib.auth.models as dj_auth_models
import django.core.paginator as dj_paginator
import django.forms as dj_forms

from . import SpecialPage as _SP, Redirect
from .. import pages
from ..namespaces import *
from .... import models, requests, forms


class SpecialPageSubpages(_SP):
    """This special page lists all subpages of a specific page.

    Args: ``/<page_name:str>``
        - ``page_name``: the name of the page to list subpages of.
    """

    def __init__(self):
        super().__init__(name='Subpages', accesskey='u')

    def _process_request(self, params: requests.RequestParams, args: list[str]) -> dict[str, _typ.Any] | Redirect:
        form = _Form()
        if params.post:
            form = _Form(params.post)
            if form.is_valid():
                return Redirect(NS_SPECIAL.get_full_page_title(self.name) + f'/{form.cleaned_data["page_name"]}')
        target_page = None
        subpages = dj_auth_models.EmptyManager(models.PageRevision)
        if title := '/'.join(args):
            target_page = pages.get_page(*pages.split_title(title))
            subpages = target_page.get_subpages()
        paginator = dj_paginator.Paginator(subpages, params.results_per_page)
        return {
            'title_key': 'title_page' if target_page else 'title',
            'title_value': target_page.full_title if target_page else None,
            'target_page': target_page,
            'subpages': paginator,
            'form': form,
            'max_page_index': paginator.num_pages,
        }


class _Form(forms.WikiForm):
    page_name = dj_forms.CharField(
        label='page',
        max_length=200,
        min_length=1,
        required=True,
        strip=True,
        validators=[models.page_title_validator],
    )

    def __init__(self, post=None, initial=None):
        super().__init__('subpages', False, post, initial)
