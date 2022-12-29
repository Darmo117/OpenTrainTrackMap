"""This module defines a page handler class for non-wiki pages."""
import abc as _abc

from . import _core
from ..api import data_types as _data_types


class OTTMHandler(_core.PageHandler, _abc.ABC):
    """Base class for non-wiki pages handlers."""

    def get_page_titles(self, page_id: str, gender: _data_types.UserGender = None,
                        titles_args: dict[str, str] = None) -> tuple[str, str]:
        """Return the localized title and tab title for the given page ID.

        :param page_id: ID of the page.
        :param gender: Gender of the targetted user.
        :param titles_args: Dict object containing values to use in the page title translation.
        :return: A tuple containing the page’s localized title and tab title.
        """
        if titles_args is None:
            titles_args = {}
        language = self._request_params.ui_language
        title = language.translate(f'page.{page_id}.title', gender=gender, **titles_args)
        tab_title = language.translate(f'page.{page_id}.tab_title', gender=gender, **titles_args)
        return title, tab_title
