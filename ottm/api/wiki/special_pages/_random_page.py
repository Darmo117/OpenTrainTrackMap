"""This module defines the random page special page."""
import random as _random
import typing as _typ

from . import _core
from .. import namespaces as _ns, pages as _pages
from .... import models as _models, requests as _requests


class RandomPageSpecialPage(_core.SpecialPage):
    """This special page redirects to a random content page or the main page if none exist."""

    def __init__(self):
        super().__init__(name='RandomPage', accesskey='x')

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        content_namespaces = [ns_id for ns_id, ns in _ns.NAMESPACE_IDS.items() if ns.is_content]
        query_set = _models.Page.objects.filter(namespace_id__in=content_namespaces)
        if query_set.count() != 0:
            page = query_set[_random.randint(0, query_set.count() - 1)]
            return _core.Redirect(page_title=page.full_title)
        return _core.Redirect(page_title=_pages.MAIN_PAGE_TITLE)
