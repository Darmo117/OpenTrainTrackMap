"""This module defines the user contributions special page."""
import typing as _typ

import django.contrib.auth.models as dj_auth_models
import django.core.paginator as dj_paginator

from . import SpecialPage as _SP, Redirect
from ... import auth as _auth
from ...permissions import *
from .... import models, requests


class SpecialPageContributions(_SP):
    """This special page lists all contributions of a specific user.

    Args: ``/<username:str>``
        - ``username``: the username of the user to display the contributions of.
    """

    def __init__(self):
        super().__init__(name='Contributions', accesskey='c')

    def _process_request(self, params: requests.RequestParams, *args: str) -> dict[str, _typ.Any] | Redirect:
        user = _auth.get_user_from_request(params.request)
        target_user = _auth.get_user_from_name(args[0]) if args else None
        if target_user:
            query_set = target_user.internal_object.pagerevision_set
            if user.has_permission(PERM_WIKI_MASK):
                contributions = query_set.all()
            else:
                contributions = query_set.filter(hidden=False)
        else:
            contributions = dj_auth_models.EmptyManager(models.PageRevision)
        paginator = dj_paginator.Paginator(contributions, params.results_per_page)
        return {
            'title_key': 'title_user' if target_user else 'title',
            'title_value': target_user.username if target_user else None,
            'target_user': target_user,
            'contributions': paginator,
            'max_page_index': paginator.num_pages,
        }
