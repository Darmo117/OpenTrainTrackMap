"""This module defines all user groups."""
GROUP_SUPERUSERS = 'superusers'
GROUP_GROUPS_MANAGERS = 'groups_managers'
GROUP_ADMINISTRATORS = 'administrators'
GROUP_WIKI_ADMINISTRATORS = 'wiki_administrators'
GROUP_PATROLLERS = 'patrollers'
GROUP_WIKI_PATROLLERS = 'wiki_patrollers'
GROUP_WIKI_AUTOPATROLLED = 'wiki_autopatrolled'
GROUP_AUTOPATROLLED = 'autopatrolled'
GROUP_USERS = 'users'
GROUP_ALL = 'all'

GROUPS: tuple[str, ...] = tuple(v for k, v in globals().items() if k.startswith('GROUP_'))
