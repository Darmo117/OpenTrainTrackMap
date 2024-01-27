"""This module defines various classes for representing data."""
from __future__ import annotations

import dataclasses as _dc
import datetime as _dt
import re as _re


class PartialDate:
    PATTERN = _re.compile(r'^(\d{4})-(\d\d|\?\?)-(\d\d|\?\?)$')

    def __init__(self, year: int, month: int = None, day: int = None):
        """Create a new partial date.

        :param year: The date’s year. Must be ≥ 0 and ≤ 9999.
        :param month: Optional. The date’s month. Must be between 1 and 12 inclusive.
        :param day: Optional. The month’s day. Must be a valid day for the given month.
        :raise ValueError: If any of the following conditions is true:
            - the year is undefined or ≤ 0
            - the month is undefined but the day is
            - the month is not between 1 and 12 inclusive
            - the day is invalid for the given month
        """
        if not isinstance(year, int) or year < 0 or year > 9999:
            raise ValueError(f'Invalid year: {year}')
        month_def = month is not None
        day_def = day is not None
        if not month_def and day_def:
            raise ValueError('Day cannot be set while month is undefined')
        if month_def:
            if month < 1 or month_def > 12:
                raise ValueError(f'Invalid month: {month}')
            if day_def:
                self._check_date(year, month, day)
        self._year = year
        self._month = month
        self._day = day

    @property
    def year(self) -> int:
        """This date’s year."""
        return self._year

    @property
    def month(self) -> int | None:
        """This date’s month (between 1 and 12) or None if undefined."""
        return self._month

    @property
    def day(self) -> int | None:
        """This date’s day of month or None if undefined."""
        return self._day

    def __eq__(self, other: PartialDate) -> bool:
        return self.year == other.year and self.month == other.month and self.day == other.day

    def __lt__(self, other: PartialDate) -> bool:
        """Check whether this date precedes the given one.

        :param other: A date to check against this one.
        :return: True if this date precedes the given one, false otherwise.
        """
        return (
                self.year < other.year
                or self.year == other.year and (
                        (self.month or 1) < (other.month or 1)
                        or (self.month or 1) == (other.month or 1) and (
                                (self.day or 1) < (other.day or 1)
                        )
                )
        )

    def __gt__(self, other: PartialDate) -> bool:
        """Check whether this date follows the given one.

        :param other: A date to check against this one.
        :return: True if this date follows the given one, false otherwise.
        """
        return (
                self.year > other.year
                or self.year == other.year and (
                        (self.month or 1) > (other.month or 1)
                        or (self.month or 1) == (other.month or 1) and (
                                (self.day or 1) > (other.day or 1)
                        )
                )
        )

    def __repr__(self) -> str:
        """Convert this date to a string in the format ``YYYY-MM-DD``
        where ``MM`` and ``DD`` can be ``??`` if either of those is None.
        """
        month = '{:02}'.format(self.month) if self.month else '??'
        day = '{:02}'.format(self.day) if self.day else '??'
        return f'{self.year:04}-{month}-{day}'

    @classmethod
    def parse(cls, s: str) -> PartialDate:
        """Parse the given string into a ``PartialDate`` object.

        :param s: The string to parse.
        :return: A new ``PartialDate`` object.
        :raise ValueError: If the string does not represent a valid partial date.
        """
        m = cls.PATTERN.fullmatch(s)
        if not m:
            raise ValueError(f'Invalid partial date string: {s}')
        year = int(m.group(1))
        month = m.group(2)
        day = m.group(3)
        if month != '??':
            if day != '??':
                return cls(year, int(month), int(day))
            return cls(year, int(month))
        return cls(year)

    @classmethod
    def now(cls) -> PartialDate:
        """Return a ``PartialDate`` instance representing the current server date.
        The month and day or guaranteed to be set.
        """
        date = _dt.datetime.now()
        return cls(date.year, date.month, date.day)

    @staticmethod
    def _check_date(y: int, m: int, d: int):
        """Check whether the given year/month/day combination is valid.

        :raise ValueError: If it is not.
        """
        leap_year = y % 4 == 0 and y % 100 != 0 or y % 400 == 0
        if (d < 1
                or m in (1, 3, 5, 7, 8, 10, 12) and d > 31
                or m in (4, 6, 9, 11) and d > 30
                or m == 2 and (leap_year and d > 29 or not leap_year and d > 28)):
            raise ValueError(f'Invalid day: {d}')


class DateInterval:  # TODO test
    """A date interval represents a period on the timeline between two dates (inclusive).
    Each boundary date may be set as approximate. If no end date is defined, the property ``is_current``
    indicates whether the interval has still not ended at the current time.
    """
    PATTERN = _re.compile(r'^\[(~?\d{4}(?:-(?:\d\d|\?\?)){2}|\?),\s*(~?\d{4}(?:-(?:\d\d|\?\?)){2}|\?|\.{3})]$')

    def __init__(
            self,
            start_date: PartialDate = None,
            end_date: PartialDate = None,
            approx_start: bool = False,
            approx_end: bool = False,
            is_current: bool = False
    ):
        """Create a date interval.

        :param start_date: The start date. May be None.
        :param end_date: The end date (inclusive). May be None.
        :param approx_start: Optional. Whether the start date is approximate.
        :param approx_end: Optional. Whether the end date is approximate.
        :param is_current: Optional. Whether the interval is current.
        :raise ValueError:  In any of the following cases:
            - start and end dates are both undefined
            - end date precedes start date
            - start date follows end date
            - start and end date are equal
            - ``is_current`` is true and end date is set
            - ``approx_start`` is true and start date is undefined
            - ``approx_end`` is true and end date is undefined
        """
        if not start_date and not end_date:
            raise ValueError('start_date and end_date cannot be both None')
        if end_date:
            if start_date:
                if end_date == start_date:
                    raise ValueError('start_date and end_date must be different')
                if end_date < start_date:
                    raise ValueError('attempt to set start_date after end_date')
                if start_date > end_date:
                    raise ValueError('attempt to set end_date before start_date')
            if is_current:
                raise ValueError('is_current cannot be true while end_date is defined')
        elif approx_end:
            raise ValueError('approx_end cannot be true while end_date is None')
        if approx_start and not start_date:
            raise ValueError('approx_start cannot be true while start_date is None')

        self._start_date = start_date
        self._end_date = end_date
        self._approx_start_date = approx_start
        self._approx_end_date = approx_end
        self._is_current = is_current

    @property
    def start_date(self) -> PartialDate | None:
        """This interval’s start date or None if it is undefined."""
        return self._start_date

    @property
    def end_date(self) -> PartialDate | None:
        """This interval’s end date or None if it is undefined."""
        return self._end_date

    @property
    def has_approx_start_date(self) -> bool:
        """Indicates whether this interval’s start date is approximate."""
        return self._approx_start_date

    @property
    def has_approx_end_date(self) -> bool:
        """Indicates whether this interval’s end date is approximate."""
        return self._approx_end_date

    @property
    def is_current(self) -> bool:
        """Indicates whether this interval is still current."""
        return self._is_current

    def __eq__(self, other: DateInterval):
        """Check whether this interval is the exact same as the given one.

        :param other: An interval to check against this one.
        :return: True if both intervals are equal, false otherwise.
        """
        return (self.has_approx_start_date == other.has_approx_start_date
                and self.has_approx_end_date == other.has_approx_end_date
                and self.start_date == other.start_date
                and self.end_date == other.end_date
                and self.is_current == other.is_current)

    def __lshift__(self, other: DateInterval) -> bool:
        """Check whether this interval precedes the given one, with a gap in-between.

        :param other: An interval to check against this one.
        :return: True if this interval’s end date precedes the start date of the given one,
            false otherwise.
        """
        return self.end_date and other.start_date and self.end_date < other.start_date

    def __lt__(self, other: DateInterval) -> bool:
        """Check whether this interval precedes the given one, with no gap in-between.

        :param other: An interval to check against this one.
        :return: True if this interval’s end date is the same as the start date of the given one,
            false otherwise.
        """
        return self.end_date and other.start_date and self.end_date == other.start_date

    def __le__(self, _):
        return NotImplemented

    def __rshift__(self, other: DateInterval) -> bool:
        """Check whether this interval follows the given one, with a gap in-between.

        :param other: An interval to check against this one.
        :return: True if this interval’s start date follows the end date of the given one,
            false otherwise.
        """
        return self.start_date and other.end_date and self.start_date > other.end_date

    def __gt__(self, other: DateInterval) -> bool:
        """Check whether this interval follows the given one, with no gap in-between.

        :param other: An interval to check against this one.
        :return: True if this interval’s start date is the same as the and date of the given one,
            false otherwise.
        """
        return self.start_date and other.end_date and self.start_date == other.end_date

    def __ge__(self, _):
        return NotImplemented

    def overlaps(self, other: DateInterval) -> bool:
        """Check whether this interval overlaps the given one.

        :param other: An interval to check against this one.
        :return: True if this interval starts inside the given one,
            or the given one starts inside this one,
            or this start date is the given one’s end date,
            or this end date is the given one’s start date; false otherwise.
        """
        now = PartialDate.now()
        self_end = now if self.is_current else self.end_date
        other_end = now if other.is_current else other.end_date
        return (
                self.start_date and self_end
                and (  # Other starts or ends inside this
                        other.start_date and self.start_date <= other.start_date <= self_end
                        or other_end and self.start_date <= other_end <= self_end
                )
        ) or (
                other.start_date and other_end
                and (  # This starts or ends inside other
                        self.start_date and other.start_date <= self.start_date <= other_end
                        or self_end and other.start_date <= self_end <= other_end
                )
        )

    def __hash__(self):
        return (hash(self.has_approx_start_date) ^ hash(self.has_approx_end_date)
                ^ hash(self.start_date) ^ hash(self.end_date) ^ hash(self.is_current) ^ 31)

    def __repr__(self):
        """ Convert this date interval to a string in the format ``[~?<partial date>, ~?<partial date>]``
        where ``<partial date>`` is a serialized `PartialDate` object and ``~`` indicates that the following date
        is approximate. The first date is the start date, the second is the end date.

        If a date is unknown, it is replaced by a single ``?``.

        If the end date is undefined and the ``is_current`` flag is true,
        the second date is replaced by three dots (``...``).
        """
        start = str(self.start_date) if self.start_date else '?'
        if self.start_date and self.has_approx_start_date:
            start = '~' + start
        if self.is_current:
            end = '...'
        else:
            end = str(self.end_date) if self.end_date else '?'
            if self.end_date and self.has_approx_end_date and not self.is_current:
                end = '~' + end
        return f'[{start}, {end}]'

    @classmethod
    def parse(cls, s: str) -> DateInterval:
        """Parse the given string into a ``DateInterval`` object.

        :param s: The string to parse.
        :return: A new ``DateInterval`` object.
        :raise ValueError: If the string does not represent a valid date interval.
        """
        m = cls.PATTERN.fullmatch(s)
        if not m:
            raise ValueError(f'Invalid date interval string: {s}')
        approx_start, start_date = cls._extract_datetime(m, 1)
        if m.group(2) == '...':
            return cls(start_date, approx_start=approx_start, is_current=True)
        approx_end, end_date = cls._extract_datetime(m, 2)
        return cls(start_date, end_date, approx_start, approx_end)

    @staticmethod
    def _extract_datetime(m: _re.Match, index: int) -> tuple[bool, PartialDate | None]:
        """Parse the date at the given index in the match object’s groups.

        :param m: The regex match object.
        :param index: The index in the match object’s groups.
        :return: A tuple with a boolean indicating whether the date is defined (``true``) or not (``?``),
            and the corresponding ``PartialDate`` object.
        """
        s = m.group(index)
        if s == '?':
            return False, None
        approx = s[0] == '~'
        if approx:
            s = s[1:]
        return approx, PartialDate.parse(s)


@_dc.dataclass(frozen=True)
class UserGender:
    """Represents a user’s gender."""
    label: str
    i18n_label: str


GENDER_N = UserGender(label='neutral', i18n_label='n')
GENDER_F = UserGender(label='female', i18n_label='f')
GENDER_M = UserGender(label='male', i18n_label='m')

GENDERS: dict[str, UserGender] = {v.label: v for k, v in globals().items() if k.startswith('GENDER_')}
