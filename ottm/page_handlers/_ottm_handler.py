"""This module defines a page handler class for non-wiki pages."""
import abc as _abc

from . import _core


class OTTMHandler(_core.PageHandler, _abc.ABC):
    """Base class for non-wiki pages handlers."""

    def get_page_titles(self, page_id: str, titles_args: dict[str, str] = None) -> tuple[str, str]:
        """Return the localized title and tab title for the given page ID.

        :param page_id: ID of the page.
        :param titles_args: Dict object containing values to use in the page title translation.
        :return: A tuple containing the page’s localized title and tab title.
        """
        if titles_args is None:
            titles_args = {}
        language = self._request_params.ui_language
        title = language.translate(f'page.{page_id}.title', **titles_args)
        tab_title = language.translate(f'page.{page_id}.tab_title', **titles_args)
        return title, tab_title
