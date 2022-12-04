"""This module defines custom model fields."""
import datetime
import typing as typ

import django.core.exceptions as dj_exc
import django.db.models as dj_models
from django.utils.translation import gettext_lazy as _t

from .api import data_types


class DateIntervalField(dj_models.Field):
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

    def from_db_value(self, value: str | None, _expression, _connection) -> data_types.DateInterval | None:
        if value is None:
            return None
        return self._parse(value)

    def to_python(self, value: data_types.DateInterval | str | None) -> data_types.DateInterval | None:
        if value is None or isinstance(value, data_types.DateInterval):
            return value
        return self._parse(value)

    def get_prep_value(self, value: data_types.DateInterval | None) -> str | None:
        if value is None:
            return None
        start_date = value.start_date.isoformat()
        end_date = value.end_date.isoformat()
        return (f'{start_date};{int(value.fuzzy_start_date)};{end_date};'
                f'{int(value.fuzzy_end_date)};{int(value.is_current)}')

    @staticmethod
    def _parse(s: str) -> data_types.DateInterval:
        parts = s.split(';')
        if len(parts) != 5:
            raise dj_exc.ValidationError('invalid date interval data', code='date_interval_field_validation_error')
        start_date = datetime.datetime.fromisoformat(parts[0])
        approx_start = parts[1] != '0'
        end_date = datetime.datetime.fromisoformat(parts[2])
        approx_end = parts[3] != '0'
        is_current = parts[4] != '0'
        return data_types.DateInterval(start_date, approx_start, end_date, approx_end, is_current)


class CommaSeparatedStringsField(dj_models.TextField):
    """A model field that can store a list of string values."""
    description = 'Comma-separated strings'

    def from_db_value(self, value: str | None, _expression, _connection) -> typ.Sequence[str] | None:
        if value is None:
            return None
        return self._parse(value)

    def to_python(self, value: typ.Sequence[float] | None | str) -> typ.Sequence[str] | None:
        if isinstance(value, typ.Sequence):
            return value
        if value is None:
            return None
        return self._parse(value)

    def get_prep_value(self, value: typ.Sequence[str] | None) -> str | None:
        if value is None:
            return None
        return ','.join(value)

    def value_to_string(self, obj) -> str | None:
        return self.get_prep_value(self.value_from_object(obj))

    @staticmethod
    def _parse(s: str) -> typ.Sequence[str]:
        return s.split(',')
