from __future__ import annotations

import django.core.exceptions as _dj_exc
import django.db.models as _dj_models

from .. import settings as _settings


class DateTimeFormat(_dj_models.Model):
    format = _dj_models.CharField(max_length=50)


class Language(_dj_models.Model):
    DIRECTIONS = ('ltr', 'rtl')

    code = _dj_models.CharField(max_length=20, unique=True)
    name = _dj_models.CharField(max_length=100, unique=True)
    writing_direction = _dj_models.CharField(max_length=3, choices=tuple((d, d) for d in DIRECTIONS))
    available_for_ui = _dj_models.BooleanField(default=False)
    default_datetime_format = _dj_models.ForeignKey(DateTimeFormat, on_delete=_dj_models.PROTECT)

    @classmethod
    def get_default(cls) -> Language:
        return cls.objects.get(code=_settings.DEFAULT_LANGUAGE_CODE)

    def delete(self, using=None, keep_parents=False):
        if self.available_for_ui:
            raise _dj_exc.ValidationError('cannot delete UI language', code='delete_ui_language')
        super().delete(using=using, keep_parents=keep_parents)
