"""This module defines the user contributions special page."""
import typing as typ

from django.core.handlers import wsgi as dj_wsgi

from . import SpecialPage
from ..api import auth


class SpecialPageContributions(SpecialPage):
    """This special page lists all contributions of a specific user.

    Args: ``/<username:str>``
        - ``username``: the username of the user to display the contributions of.
    """

    def __init__(self):
        super().__init__(name='Contributions')

    def _process_request(self, request: dj_wsgi.WSGIRequest, *args: str, **kwargs: str) -> dict[str, typ.Any]:
        user = auth.get_user_from_request(request)
        target_user = auth.get_user_from_name(args[0]) if len(args) else user
        # TODO