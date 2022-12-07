"""This module defines the wiki’s namespaces."""
import dataclasses

SEPARATOR = ':'


@dataclasses.dataclass(frozen=True)
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


NS_SPECIAL = Namespace(id=-1, name='Special', is_editable=False, allows_subpages=False)
NS_MAIN = Namespace(id=0, name='', is_content=True, allows_subpages=False)
NS_CATEGORY = Namespace(id=1, name='Category', allows_subpages=False)
NS_WIKI = Namespace(id=2, name='Wiki')
NS_HELP = Namespace(id=3, name='Help')
NS_USER = Namespace(id=4, name='User')
NS_TEMPLATE = Namespace(id=10, name='Template')
NS_MODULE = Namespace(id=11, name='Module')
NS_INTERFACE = Namespace(id=12, name='Interface')
NS_FILE = Namespace(id=13, name='File', allows_subpages=False)

NAMESPACES: dict[int, Namespace] = {v.id: v for k, v in globals().items() if k.startswith('NS_')}
NAMESPACES_NAMES: dict[str, Namespace] = {k: v for k, v in globals().items() if k.startswith('NS_')}


def resolve_name(ns_name: str) -> Namespace | None:
    """Return the namespace for the given name.

    :param ns_name: Namespace name to resolve.
    :return: The namespace object or None if no namespace matched.
    """
    ns_name = ns_name.lower()
    for ns_id, ns in NAMESPACES.items():
        if ns.name.lower() == ns_name:
            return ns
    return None
