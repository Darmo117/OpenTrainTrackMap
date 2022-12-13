"""This module defines the user contributions special page."""
import typing as _typ

from django.core.handlers import wsgi as _dj_wsgi

from . import SpecialPage as _SP
from ... import auth as _auth


class SpecialPageContributions(_SP):
    """This special page lists all contributions of a specific user.

    Args: ``/<username:str>``
        - ``username``: the username of the user to display the contributions of.
    """

    def __init__(self):
        super().__init__(name='Contributions', accesskey='c')

    def _process_request(self, request: _dj_wsgi.WSGIRequest, *args: str, **kwargs: str) -> dict[str, _typ.Any]:
        user = _auth.get_user_from_request(request)
        target_user = _auth.get_user_from_name(args[0]) if len(args) else user
        # TODO
