"""This module defines custom model fields."""
import datetime
import typing as typ

import django.core.exceptions as dj_exc
import django.db.models as dj_models

from . import classes


class TimeIntervalField(dj_models.Field):
    """A model field that can store a TimeInterval object."""
    description = 'Time interval with possibly fuzzy bounds'

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 45
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['max_length']
        return name, path, args, kwargs

    def get_internal_type(self):
        return 'CharField'

    def from_db_value(self, value, _expression, _connection):
        if value is None:
            return None
        return self._parse(value)

    def to_python(self, value):
        if isinstance(value, classes.TimeInterval):
            return value
        if value is None:
            return None
        return self._parse(value)

    def get_prep_value(self, value: typ.Optional[classes.TimeInterval]):
        if value is None:
            return None
        start_date = value.start_date.isoformat()
        end_date = value.end_date.isoformat()
        return (f'{start_date};{int(value.approximate_start_date)};{end_date};'
                f'{int(value.approximate_end_date)};{int(value.is_current)}')

    def value_to_string(self, obj):
        return self.get_prep_value(self.value_from_object(obj))

    @staticmethod
    def _parse(s: str) -> classes.TimeInterval:
        parts = s.split(';')
        if len(parts) != 5:
            raise dj_exc.ValidationError('invalid input for TimeInterval instance')
        start_date = datetime.datetime.fromisoformat(parts[0])
        approx_start = parts[1] != '0'
        end_date = datetime.datetime.fromisoformat(parts[2])
        approx_end = parts[3] != '0'
        is_current = parts[4] != '0'
        return classes.TimeInterval(start_date, approx_start, end_date, approx_end, is_current)


class CommaSeparatedFloatField(dj_models.CharField):
    """A model field that can store a list of float values."""
    description = 'Comma-separated floats'

    def from_db_value(self, value, _expression, _connection):
        if value is None:
            return None
        return self._parse(value)

    def to_python(self, value):
        if isinstance(value, typ.Sequence):
            return value
        if value is None:
            return None
        return self._parse(value)

    def get_prep_value(self, value: typ.Optional[typ.List[float]]):
        if value is None:
            return None
        return ','.join(map(str, value))

    def value_to_string(self, obj):
        return self.get_prep_value(self.value_from_object(obj))

    @staticmethod
    def _parse(s: str) -> typ.List[float]:
        try:
            return [float(p) for p in s.split(',')]
        except ValueError as e:
            raise dj_exc.ValidationError(str(e))
