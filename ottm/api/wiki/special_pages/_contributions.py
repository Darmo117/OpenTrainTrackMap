"""This module defines the user contributions special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.core.paginator as _dj_paginator
import django.forms as _dj_forms

from . import _core
from ..namespaces import *
from ... import auth as _auth
from ...permissions import *
from .... import models as _models, page_handlers as _ph, requests as _requests


class ContributionsSpecialPage(_core.SpecialPage):
    """This special page lists all contributions of a specific user.

    Args: ``/<username:str>``
        - ``username``: the username of the user to display the contributions of.
    """

    def __init__(self):
        super().__init__('Contributions', accesskey='c', category=_core.Section.USERS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        user = _auth.get_user_from_request(params.request)
        form = _Form()
        if params.post:
            form = _Form(params.post)
            if form.is_valid():
                return _core.Redirect(NS_SPECIAL.get_full_page_title(self.name) + f'/{form.cleaned_data["username"]}')
        target_user = None
        contributions = _dj_auth_models.EmptyManager(_models.PageRevision)
        global_errors = {form.name: []}
        if args:
            target_user = _auth.get_user_from_name(args[0])
            if not target_user:
                global_errors[form.name].append('user_does_not_exist')
                form = _Form(initial={'username': args[0]})
            else:
                query_set = target_user.internal_object.pagerevision_set
                if user.has_permission(PERM_MASK):
                    contributions = query_set.all()
                else:
                    contributions = query_set.filter(hidden=False)
                form = _Form(initial={'username': target_user.username})
        paginator = _dj_paginator.Paginator(contributions.reverse(), params.results_per_page)
        return {
            'title_key': 'title_user' if target_user else 'title',
            'title_value': target_user.username if target_user else None,
            'target_user': target_user,
            'contributions': paginator,
            'form': form,
            'max_page_index': paginator.num_pages,
            'global_errors': global_errors,
        }


class _Form(_ph.WikiForm):
    username = _dj_forms.CharField(
        label='username',
        max_length=_dj_auth_models.AbstractUser._meta.get_field('username').max_length,
        required=True,
        strip=True,
        validators=[_models.username_validator],
    )

    def __init__(self, post=None, initial=None):
        super().__init__('select_user', False, post=post, initial=initial)
