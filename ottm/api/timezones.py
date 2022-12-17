"""This module defines timezone-related data."""
import pytz as _pytz


def _group() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Format pytz’s timezone list to be usable by ChoiceField objects."""
    groups = []
    group = None
    for tz in _pytz.all_timezones:
        zone = tz.split('/')[0]
        if group is None or group[0] != zone:
            if group is not None:
                groups.append((group[0], tuple(group[1])))
            group = (zone, [])
        group[1].append((tz, tz))
    return tuple(groups)


TIMEZONES = tuple(_pytz.all_timezones)
GROUPED_TIMEZONES = _group()
