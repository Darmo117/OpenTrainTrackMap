"""This module defines various classes for representing data."""
from __future__ import annotations

import datetime
import typing as typ


class TimeInterval:
    def __init__(self, start_date: typ.Optional[datetime.datetime], approx_start: bool,
                 end_date: typ.Optional[datetime.datetime], approx_end: bool, is_current: bool = False):
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
        self._start_date = start_date
        if self._start_date:
            self._start_date = self._start_date.replace(tzinfo=None)
        self.approximate_start_date = approx_start
        self._end_date = end_date
        if self._end_date:
            self._end_date = self._end_date.replace(tzinfo=None)
        self.approximate_end_date = approx_end
        # Whether this time interval still exists to this day when no end date is specified.
        self._is_current = is_current
        self._check()

    @property
    def start_date(self) -> typ.Optional[datetime.datetime]:
        """The start date of this interval."""
        return self._start_date

    @start_date.setter
    def start_date(self, value: typ.Optional[datetime.datetime]):
        self._check(with_value=value, attr_name='_start_date')
        self._start_date = value
        if self._start_date:
            self._start_date = self._start_date.replace(tzinfo=None)

    @property
    def end_date(self) -> typ.Optional[datetime.datetime]:
        """The end date of this interval."""
        return self._end_date

    @end_date.setter
    def end_date(self, value: typ.Optional[datetime.datetime]):
        self._check(with_value=value, attr_name='_end_date')
        self._end_date = value
        if self._end_date:
            self._end_date = self._end_date.replace(tzinfo=None)
            self._is_current = False

    @property
    def is_current(self) -> bool:
        """Whether this interval with no end date is still current."""
        return self._is_current

    @is_current.setter
    def is_current(self, value: bool):
        self._check(with_value=value, attr_name='_is_current')
        self._is_current = value

    def _check(self, with_value=None, attr_name: str = None):
        start_date = self._start_date if attr_name != '_start_date' else with_value
        end_date = self._end_date if attr_name != '_end_date' else with_value
        is_current = self._is_current if attr_name != '_is_current' else with_value
        now = datetime.datetime.now()
        if is_current:
            if end_date:
                raise ValueError('"is_current" attribute cannot be true while an end date is defined')
        if start_date and end_date and end_date < start_date:
            raise ValueError('start date is after end date')
        if start_date and start_date > now:
            raise ValueError('start date is in the future')
        if end_date and end_date > now:
            raise ValueError('end date is in the future')

    def overlaps(self, other: TimeInterval) -> typ.Optional[bool]:
        """Checks whether this property’s time interval overlaps the given one’s.
        If an end date is undefined but the property still applies is True, the current date will be used.

        :param other: The property to check against.
        :return: True if the time intervals are overlapping; False otherwise; None if it cannot be evaluated.
        """
        now = datetime.datetime.now()
        self_end = now if self.is_current else self.end_date
        other_end = now if other.is_current else other.end_date
        self_overlaps = (self.start_date and self_end
                         and (other.start_date and self.start_date <= other.start_date <= self_end
                              or other_end and self.start_date <= other_end <= self_end))
        overlaps = self_overlaps and (other.start_date and other_end
                                      and (self.start_date and other.start_date <= self.start_date <= other_end
                                           or self_end and other.start_date <= self_end <= other_end))
        return overlaps

    @property
    def timedelta(self) -> typ.Optional[datetime.timedelta]:
        """The time delta between the start and end dates. May be None if any of them is undefined.
        If end date is undefined but still_exists is True, the current date will be used.
        """
        end = datetime.datetime.now() if self.is_current else self.end_date
        return (self.start_date - end) if self.start_date and end else None

    def __str__(self):
        start = self.start_date.isoformat(sep=' ') if self.start_date else '?'
        if self.start_date and self.approximate_start_date:
            start = '~' + start
        if self.is_current:
            end = '…'
        else:
            end = self.end_date.isoformat(sep=' ') if self.end_date else '?'
            if self.end_date and self.approximate_end_date and not self.is_current:
                end = '~' + end
        return f'[{start}, {end}]'
