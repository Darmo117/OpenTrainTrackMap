"""This module handles background tasks."""
import typing as _typ
from apscheduler.schedulers import background as _aps_bg

from .. import settings as _settings

_REGISTRY = []


def register(frequency: int, interval: str):
    """Decorator to register a function (signature: () -> None) as a background task."""

    def wrapper(func: _typ.Callable[[], None]) -> _typ.Callable[[], None]:
        _settings.LOGGER.info(f'Register background task {func.__name__} (every {frequency} {interval}).')
        _REGISTRY.append((func, frequency, interval))
        return func

    return wrapper


def start():
    """Start all background tasks."""
    # noinspection PyUnresolvedReferences
    from .wiki import tasks  # Import to register all tasks now
    scheduler = _aps_bg.BackgroundScheduler()
    for func, frequency, interval in _REGISTRY:
        scheduler.add_job(func, 'interval', **{interval: frequency})
    scheduler.start()
    _settings.LOGGER.info(f'Started {len(_REGISTRY)} background tasks.')
