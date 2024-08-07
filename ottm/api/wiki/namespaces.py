"""This module defines the wiki’s namespaces."""
import dataclasses as _dt

from .. import permissions as _perms

SEPARATOR = ':'


@_dt.dataclass(frozen=True)
class Namespace:
    """Pages in different namespaces have different behaviors depending on the namespace’s configuration."""
    id: int
    name: str
    is_content: bool = False
    allows_subpages: bool = True
    perms_required: tuple[str] = ()
    is_editable: bool = True

    def get_full_page_title(self, page_title: str) -> str:
        """Return the full version of the given page title in this namespace.

        :param page_title: Page title to prepend this namespace’s name to.
        :return: The full page title in the format &lt;ns_name>:&lt;page_title>.
        """
        if self.name == '':
            return page_title
        return self.name + SEPARATOR + page_title

    def can_user_edit_pages(self, user) -> bool:
        """Check whether the given user can edit pages from this namespace.

        :param user: The user.
        :type user: ottm.models.User
        :return: True if the user is allowed, false otherwise.
        """
        return self.is_editable and all(user.has_permission(p) for p in self.perms_required)

    def get_display_name(self, language) -> str:
        """Return the name of this namespace in the given language.

        :param language: The language.
        :type language: ottm.settings.UILanguage
        :return: The namespace’s name.
        """
        if self.name:
            return self.name
        return language.translate(f'wiki.namespace.{self.id}.display_name')


NS_SPECIAL = Namespace(id=-1, name='Special', is_editable=False, allows_subpages=False)
NS_MAIN = Namespace(id=0, name='', is_content=True, allows_subpages=False)
NS_CATEGORY = Namespace(id=1, name='Category', allows_subpages=False)
NS_WIKI = Namespace(id=2, name='Wiki')
NS_HELP = Namespace(id=3, name='Help')
NS_USER = Namespace(id=4, name='User')
NS_TEMPLATE = Namespace(id=10, name='Template')
NS_MODULE = Namespace(id=11, name='Module')
NS_INTERFACE = Namespace(id=12, name='Interface', perms_required=(_perms.PERM_WIKI_EDIT_INTERFACE,))
NS_FILE = Namespace(id=13, name='File', allows_subpages=False)

NAMESPACE_IDS: dict[int, Namespace] = {v.id: v for k, v in globals().items() if k.startswith('NS_')}
NAMESPACE_NAMES: dict[str, Namespace] = {v.name: v for k, v in globals().items() if k.startswith('NS_')}
NAMESPACES_DICT: dict[str, Namespace] = {k: v for k, v in globals().items() if k.startswith('NS_')}
