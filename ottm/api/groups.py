GROUP_SUPERUSER = 'superuser'
GROUP_ADMINISTRATOR = 'administrator'
GROUP_WIKI_ADMINISTRATOR = 'wiki_administrator'
GROUP_PATROLLER = 'patroller'
GROUP_WIKI_PATROLLER = 'wiki_patroller'
GROUP_WIKI_AUTOPATROLLED = 'wiki_autopatrolled'
GROUP_AUTOPATROLLED = 'autopatrolled'
GROUP_USER = 'user'
GROUP_ALL = 'all'

GROUPS: tuple[str, ...] = tuple(v for k, v in globals().items() if k.startswith('GROUP_'))
