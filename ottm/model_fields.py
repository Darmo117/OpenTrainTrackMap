"""This module defines custom model fields."""
import datetime
import typing as _typ

import django.core.exceptions as _dj_exc
import django.db.models as _dj_models
from django.utils.translation import gettext_lazy as _t

from .api import data_types as _dt


class DateIntervalField(_dj_models.Field):
    """A model field that can store a DateInterval object."""
    description = _t('A date interval with possibly fuzzy bounds.')

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 45
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['max_length']
        return name, path, args, kwargs

    def get_internal_type(self):
        return 'CharField'

    def from_db_value(self, value: str | None, _expression, _connection) -> _dt.DateInterval | None:
        if value is None:
            return None
        return self.parse(value)

    def to_python(self, value: _dt.DateInterval | str | None) -> _dt.DateInterval | None:
        if value is None or isinstance(value, _dt.DateInterval):
            return value
        return self.parse(value)

    def get_prep_value(self, value: _dt.DateInterval | None) -> str | None:
        if value is None:
            return None
        return self.to_string(value)

    @staticmethod
    def to_string(value: _dt.DateInterval) -> str:
        start_date = value.start_date.isoformat()
        end_date = value.end_date.isoformat()
        return (f'{start_date};{int(value.fuzzy_start_date)};{end_date};'
                f'{int(value.fuzzy_end_date)};{int(value.is_current)}')

    @staticmethod
    def parse(s: str) -> _dt.DateInterval:
        parts = s.split(';')
        if len(parts) != 5:
            raise _dj_exc.ValidationError('invalid date interval data', code='date_interval_field_validation_error')
        start_date = datetime.datetime.fromisoformat(parts[0])
        approx_start = parts[1] != '0'
        end_date = datetime.datetime.fromisoformat(parts[2])
        approx_end = parts[3] != '0'
        is_current = parts[4] != '0'
        return _dt.DateInterval(start_date, approx_start, end_date, approx_end, is_current)


class CommaSeparatedStringsField(_dj_models.TextField):
    """A model field that can store a list of string values."""
    description = 'Comma-separated strings'

    def __init__(self, separator: str = ',', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._separator = separator

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self._separator != ',':
            kwargs['separator'] = self._separator
        return name, path, args, kwargs

    @property
    def separator(self) -> str:
        return self._separator

    def from_db_value(self, value: str | None, _expression, _connection) -> _typ.Sequence[str] | None:
        if value is None:
            return None
        return self._parse(value)

    def to_python(self, value: _typ.Sequence[float] | None | str) -> _typ.Sequence[str] | None:
        if isinstance(value, _typ.Sequence):
            return value
        if value is None:
            return None
        return self._parse(value)

    def get_prep_value(self, value: _typ.Sequence[str] | None) -> str | None:
        if value is None:
            return None
        return self._separator.join(v for v in value if v)

    def value_to_string(self, obj) -> str | None:
        return self.get_prep_value(self.value_from_object(obj))

    def _parse(self, value: str) -> list[str]:
        return [s for s in value.split(self._separator) if s]
