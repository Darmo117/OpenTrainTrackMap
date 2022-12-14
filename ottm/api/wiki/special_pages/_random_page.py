"""This module defines the random page special page."""
import random
import typing as _typ

from django.core.handlers import wsgi as _dj_wsgi

from . import SpecialPage as _SP, Redirect
from .. import namespaces, pages
from .... import models, requests


class SpecialPageRandomPage(_SP):
    """This special page redirects to a random content page or the main page if none exist."""

    def __init__(self):
        super().__init__(name='RandomPage', accesskey='x')

    def _process_request(self, params: requests.RequestParams, *args: str) -> dict[str, _typ.Any] | Redirect:
        content_namespaces = [ns_id for ns_id, ns in namespaces.NAMESPACE_IDS.items() if ns.is_content]
        query_set = models.Page.objects.filter(namespace_id__in=content_namespaces)
        if query_set.count() != 0:
            page = query_set[random.randint(0, query_set.count() - 1)]
            return Redirect(page_title=page.full_title)
        return Redirect(page_title=pages.MAIN_PAGE_TITLE)
