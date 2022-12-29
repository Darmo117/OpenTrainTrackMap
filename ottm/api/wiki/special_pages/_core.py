"""Core module of the special_pages package."""
import abc as _abc
import dataclasses as _dt
import enum as _enum
import typing as _typ

from .... import models as _models, requests as _requests


class Section(_enum.Enum):
    MAINTENANCE = 'maintenance'
    PAGE_LISTS = 'page_lists'
    PAGE_OPERATIONS = 'page_operations'
    USERS = 'users'
    LOGS = 'logs'
    FILES = 'files'
    DATA_TOOLS = 'data_tools'
    REDIRECTS = 'redirects'
    MOST_USED_PAGES = 'most_used_pages'
    OTHER = 'other'


@_dt.dataclass(frozen=True)
class Redirect:
    page_title: str
    args: dict[str, _typ.Any] = _dt.field(default_factory=lambda: {})


class SpecialPage(_abc.ABC):
    """Base class for special pages."""

    def __init__(self, name: str, *requires_perms: str, has_custom_css: bool = False, has_custom_js: bool = False,
                 accesskey: str = None, category: Section = None):
        """Create a special page.

        :param name: Page’s name.
        :param requires_perms: List of permissions required to access this page.
        :param has_custom_css: Whether this page has custom CSS.
        :param has_custom_js: Whether this page has custom JS.
        :param accesskey: The access key for menu links that point to this page.
        :param category: The page’s category.
        """
        self._name = name
        self._has_custom_css = has_custom_css
        self._has_custom_js = has_custom_js
        self._perms_required = requires_perms
        self._accesskey = accesskey
        self._category = category

    @property
    def name(self) -> str:
        """This page’s name."""
        return self._name

    @property
    def has_custom_css(self) -> bool:
        """Whether this page has custom CSS."""
        return self._has_custom_css

    @property
    def has_custom_js(self) -> bool:
        """Whether this page has custom JS."""
        return self._has_custom_js

    @property
    def permissions_required(self) -> tuple[str, ...]:
        """The permissions required to access this page."""
        return self._perms_required

    @property
    def access_key(self) -> str | None:
        """The access key for menu links that point to this page."""
        return self._accesskey

    @property
    def category(self) -> Section | None:
        """This page’s category."""
        return self._category

    def can_user_access(self, user: _models.User) -> bool:
        """Check whether the given user can access this page."""
        return all(user.has_permission(p) for p in self.permissions_required)

    def process_request(self, params: _requests.RequestParams, title: str) -> dict[str, _typ.Any] | Redirect:
        """Process the given client request.

        :param params: Page’s request parameters.
        :param title: Page’s full title. The title will be split around '/'.
        :return: A dict object containing parameters to pass to the page context object.
        """
        data = self._process_request(params, title.split('/')[1:])
        if isinstance(data, Redirect):
            return data
        if 'target_user' in data and data['target_user']:
            data['title_key'] = f'{data["title_key"]}.{data["target_user"].gender.i18n_label}'
        return {
            'has_custom_css': self.has_custom_css,
            'has_custom_js': self.has_custom_js,
            **data,
        }

    @_abc.abstractmethod
    def _process_request(self, params: _requests.RequestParams, args: list[str]) -> dict[str, _typ.Any] | Redirect:
        """Process the given client request.

        :param params: Page’s request parameters.
        :param args: Page’s arguments.
        :return: A dict object containing parameters to pass to the page context object.
        """
        pass
