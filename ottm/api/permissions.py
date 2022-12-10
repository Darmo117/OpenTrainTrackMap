"""This module defines all user permissions used througout the website."""
# OTTM
PERM_EDIT_SCHEMA = 'edit_schema'
PERM_EDIT_OBJECTS = 'edit_objects'
PERM_EDIT_USER_GROUPS = 'edit_user_groups'
PERM_REVERT = 'revert'
PERM_BLOCK_USERS = 'block_users'
# Wiki
PERM_WIKI_EDIT = 'wiki_edit'
PERM_WIKI_DELETE = 'wiki_delete'
PERM_WIKI_RENAME = 'wiki_rename'
PERM_WIKI_REVERT = 'wiki_revert'
PERM_WIKI_PROTECT = 'wiki_protect'
PERM_WIKI_MASK = 'wiki_mask'
PERM_WIKI_EDIT_FILTERS = 'wiki_edit_filters'
PERM_WIKI_BLOCK_USERS = 'wiki_block_users'
PERM_WIKI_EDIT_USER_PAGES = 'wiki_edit_user_pages'
PERM_WIKI_EDIT_INTERFACE = 'wiki_edit_interface'

PERMS: tuple[str, ...] = tuple(v for k, v in globals().items() if k.startswith('PERM_'))
