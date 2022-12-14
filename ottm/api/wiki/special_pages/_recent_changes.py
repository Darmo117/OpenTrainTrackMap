"""This module defines the recent changes special page."""
import typing as _typ

from django.core.handlers import wsgi as _dj_wsgi

from . import SpecialPage as _SP
from ... import auth as _auth
from .... import requests


class SpecialPageRecentChanges(_SP):
    """This special page lists all recent page edits."""

    def __init__(self):
        super().__init__(name='RecentChanges', accesskey='c')

    def _process_request(self, params: requests.RequestParams, *args: str, ) -> dict[str, _typ.Any]:
        user = _auth.get_user_from_request(params.request)
        target_user = _auth.get_user_from_name(args[0]) if len(args) else user
        # TODO
