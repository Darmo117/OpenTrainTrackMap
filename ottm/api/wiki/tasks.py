"""Wiki’s background tasks."""
from . import pages as _pages
from .. import auth as _auth, bg_tasks as _bg_tasks, utils as _utils
from ... import models as _models, settings as _settings


@_bg_tasks.register(frequency=10, interval='minutes')
def refresh_page_caches():
    """Refresh the cache of all non-deleted pages whose expiry date is passed."""
    _settings.LOGGER.info('Refreshing page caches…')
    wiki_user = _auth.get_user_from_name(_settings.WIKI_SETUP_USERNAME)
    now = _utils.now()
    nb = 0
    for page in _models.Page.objects.filter(deleted=False, cache_expiry_date__lte=now):
        _pages.edit_page(wiki_user, page, page.get_latest_revision().content)
        nb += 1
    _settings.LOGGER.info(f'Refreshed {nb} page(s).')


@_bg_tasks.register(frequency=1, interval='hours')
def delete_expired_page_protections():
    """Delete all page protections that have expired."""
    _settings.LOGGER.info('Deleting expired page protections…')
    now = _utils.now()
    nb = 0
    for pp in _models.PageProtection.objects.filter(end_date__lte=now):
        pp.delete()
        nb += 1
    _settings.LOGGER.info(f'Deleted {nb} page protection(s).')


@_bg_tasks.register(frequency=1, interval='hours')
def delete_expired_page_follows():
    """Delete all pages follows that have expired."""
    _settings.LOGGER.info('Deleting expired page follows…')
    now = _utils.now()
    nb = 0
    for pfs in _models.PageFollowStatus.objects.filter(end_date__lte=now):
        pfs.delete()
        nb += 1
    _settings.LOGGER.info(f'Deleted {nb} page follow(s).')


@_bg_tasks.register(frequency=1, interval='hours')
def delete_expired_user_blocks():
    """Delete all user blocks that have expired."""
    _settings.LOGGER.info('Deleting expired user blocks…')
    now = _utils.now()
    nb = 0
    for pfs in _models.UserBlock.objects.filter(end_date__lte=now):
        pfs.delete()
        nb += 1
    _settings.LOGGER.info(f'Deleted {nb} user block(s).')


@_bg_tasks.register(frequency=1, interval='hours')
def delete_expired_ip_blocks():
    """Delete all IP blocks that have expired."""
    _settings.LOGGER.info('Deleting expired IP blocks…')
    now = _utils.now()
    nb = 0
    for pfs in _models.IPBlock.objects.filter(end_date__lte=now):
        pfs.delete()
        nb += 1
    _settings.LOGGER.info(f'Deleted {nb} IP block(s).')
