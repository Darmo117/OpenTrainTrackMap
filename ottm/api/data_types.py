"""This module defines various classes for representing data."""
from __future__ import annotations

import dataclasses as _dc
import datetime as _dt
import re

from . import utils as _utils


class DateInterval:  # TODO test
    """TimeInterval objects represent time intervals whose bounds may be fuzzy.
    Instances are hashable and orderable.

    A ValueError may be raised if at least one of these situations is encountered:
        - start_date is after end_date.
        - start_date, end_date or both are in the future.
        - is_current is true and end_date is not None.
    """

    def __init__(self, start_date: _dt.datetime | None, approx_start: bool,
                 end_date: _dt.datetime | None, approx_end: bool, is_current: bool = False):
        """TimeInterval objects represent time intervals whose bounds may be fuzzy.

        A ValueError may be raised if at least one of these situations is encountered:
            - start_date is after end_date.
            - start_date, end_date or both are in the future.
            - is_current is true and end_date is not None

        :param start_date: The start date; may be None.
        :param approx_start: Whether the start date is approximate or exact.
        :param end_date: The end date; may be None.
        :param approx_end: Whether the end date is approximate or exact.
        :param is_current: In the case no end date is specified, whether the interval is still ongoing currently.
        """
        self._start_date = self._end_date = None
        if start_date:
            self.start_date = start_date.replace(tzinfo=None)
        else:
            self.start_date = None
        if end_date:
            self.end_date = end_date.replace(tzinfo=None)
        else:
            self.end_date = None
        self.fuzzy_start_date = approx_start
        self.fuzzy_end_date = approx_end
        # Whether this time interval still exists to this day when no end date is specified.
        self.is_current = is_current

    @property
    def fuzzy_start_date(self) -> bool:
        """Whether the start date is approximate."""
        return self._fuzzy_start_date

    @fuzzy_start_date.setter
    def fuzzy_start_date(self, fuzzy: bool):
        if fuzzy and self._start_date is None:
            raise ValueError('"fuzzy_start_date" attribute cannot be true while a start date is undefined')
        self._fuzzy_start_date = fuzzy

    @property
    def fuzzy_end_date(self) -> bool:
        """Whether the end date is approximate."""
        return self._fuzzy_end_date

    @fuzzy_end_date.setter
    def fuzzy_end_date(self, fuzzy: bool):
        if fuzzy and self._end_date is None:
            raise ValueError('"fuzzy_end_date" attribute cannot be true while an end date is undefined')
        self._fuzzy_end_date = fuzzy

    @property
    def start_date(self) -> _dt.datetime | None:
        """The start date of this interval."""
        return self._start_date

    @start_date.setter
    def start_date(self, start_date: _dt.datetime | None):
        if start_date and self._end_date and self._end_date < start_date:
            raise ValueError('start date after end date')
        if start_date is None and self._end_date is None:
            raise ValueError('start and end date cannot both be None')
        self._start_date = start_date
        if self._start_date:
            self._start_date = self._start_date.replace(tzinfo=None)

    @property
    def end_date(self) -> _dt.datetime | None:
        """The end date of this interval."""
        return self._end_date

    @end_date.setter
    def end_date(self, end_date: _dt.datetime | None):
        if end_date and self._start_date and end_date < self._start_date:
            raise ValueError('end date before start date')
        if self._start_date is None and end_date is None:
            raise ValueError('start and end date cannot both be None')
        self._end_date = end_date
        if self._end_date:
            self._end_date = self._end_date.replace(tzinfo=None)
            self._is_current = False

    @property
    def is_current(self) -> bool:
        """Whether this interval with no end date is still current."""
        return self._is_current

    @is_current.setter
    def is_current(self, is_current: bool):
        if is_current and self._end_date:
            raise ValueError('"is_current" attribute cannot be true while an end date is defined')
        self._is_current = is_current

    def overlaps(self, other: DateInterval) -> bool | None:
        """Checks whether this property’s time interval overlaps the given one’s.
        If an end date is undefined but the property still applies is True, the current date will be used.

        :param other: The property to check against.
        :return: True if the time intervals are overlapping; False otherwise; None if it cannot be evaluated.
        """
        now = _utils.now()
        self_end = now if self.is_current else self.end_date
        other_end = now if other.is_current else other.end_date
        return (
                self.start_date and self_end
                and (
                        other.start_date and self.start_date <= other.start_date <= self_end
                        or other_end and self.start_date <= other_end <= self_end
                )
        ) or (
                other.start_date and other_end
                and (
                        self.start_date and other.start_date <= self.start_date <= other_end
                        or self_end and other.start_date <= self_end <= other_end
                )
        )

    def __lt__(self, other: DateInterval) -> bool:
        return self.end_date is not None and other.start_date is not None and self.end_date < other.start_date

    def __le__(self, other: DateInterval) -> bool:
        return self.end_date is not None and other.start_date is not None and self.end_date <= other.start_date

    precedes = __lt__
    precedes_and_meets = __le__

    def __gt__(self, other: DateInterval) -> bool:
        return self.start_date is not None and other.end_date is not None and self.start_date > other.end_date

    def __ge__(self, other: DateInterval) -> bool:
        return self.start_date is not None and other.end_date is not None and self.start_date >= other.end_date

    follows = __gt__
    follows_and_meets = __ge__

    def __eq__(self, other: DateInterval):
        return (self.fuzzy_start_date == other.fuzzy_start_date
                and self.fuzzy_end_date == other.fuzzy_end_date
                and self.start_date == other.start_date
                and self.end_date == other.end_date
                and self.is_current == other.is_current)

    def __hash__(self):
        return (hash(self.fuzzy_start_date) ^ hash(self.fuzzy_end_date)
                ^ hash(self.start_date) ^ hash(self.end_date) ^ hash(self.is_current) ^ 31)

    def timedelta(self) -> _dt.timedelta | None:
        """The time delta between the start and end dates. May be None if any of them is undefined.
        If end date is undefined but still_exists is True, the current date will be used.
        """
        end = _utils.now() if self.is_current else self.end_date
        return (self.start_date - end) if self.start_date and end else None

    def __repr__(self):
        start = self.start_date.isoformat(sep=' ') if self.start_date else '?'
        if self.start_date and self.fuzzy_start_date:
            start = '~' + start
        if self.is_current:
            end = '…'
        else:
            end = self.end_date.isoformat(sep=' ') if self.end_date else '?'
            if self.end_date and self.fuzzy_end_date and not self.is_current:
                end = '~' + end
        return f'[{start}, {end}]'

    @classmethod
    def from_string(cls, s: str) -> DateInterval:
        m = re.fullmatch(r'\[((~?)(\d{4}(?:-\d{2}){2})|\?),\s*((~?)(\d{4}(?:-\d{2}){2})|\?|…)]', s)
        if not m:
            raise ValueError('cannot parse string')
        start_approx, start_date = cls._extract_datetime(m, 0)
        end_approx, end_date = cls._extract_datetime(m, 3)
        return DateInterval(start_date, start_approx, end_date, end_approx)

    @staticmethod
    def _extract_datetime(m: re.Match, offset: int) -> tuple[bool, _dt.datetime | None]:
        if m.group(1 + offset) == '?':
            return False, None
        return m.group(2 + offset) == '~', _dt.datetime.strptime(m.group(3 + offset), '%y-%m-%d %H:%M:%S')


@_dc.dataclass(frozen=True)
class UserGender:
    """Represents a user’s gender."""
    label: str
    i18n_label: str


GENDER_N = UserGender(label='neutral', i18n_label='n')
GENDER_F = UserGender(label='female', i18n_label='f')
GENDER_M = UserGender(label='male', i18n_label='m')

GENDERS: dict[str, UserGender] = {v.label: v for k, v in globals().items() if k.startswith('GENDER_')}
