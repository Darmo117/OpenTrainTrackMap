"""This module defines the recent changes special page."""
import typing as _typ

from . import _core
from ... import auth as _auth
from .... import requests as _requests


class RecentChangesSpecialPage(_core.SpecialPage):
    """This special page lists all recent page edits."""

    def __init__(self):
        super().__init__('RecentChanges', accesskey='c', category=_core.Section.LOGS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) -> dict[str, _typ.Any]:
        user = _auth.get_user_from_request(params.request)
        target_user = _auth.get_user_from_name(args[0]) if len(args) else user
        # TODO
