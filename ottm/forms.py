"""This module defines website’s forms."""
import typing as _typ

import django.core.exceptions as _dj_exc
import django.forms as _dj_forms


class CustomForm(_dj_forms.Form):
    """Base class for all forms. Applies custom CSS styles to widgets."""

    def __init__(self, name: str, warn_unsaved_changes: bool, sections: dict[str, dict[str, list[str]]] = None,
                 post=None, initial=None):
        super().__init__(post, initial=initial)
        self._name = name
        self._warn_unsaved_changes = warn_unsaved_changes
        if not sections:
            self._sections = {'': {'': self}}
        else:
            self._sections = {}
            for section_name, fieldsets in sections.items():
                self._sections[section_name] = {}
                for fieldset_name, field_names in fieldsets.items():
                    self._sections[section_name][fieldset_name] = [self[name] for name in field_names]
        # Set widgets’ IDs
        for field_name, field in self.fields.items():
            field.widget.attrs['id'] = f'{name.replace("_", "-")}-form-{field_name.replace("_", "-")}'
        # Add Bootstrap CSS classes to widgets
        for visible in self.visible_fields():
            if isinstance(visible.field.widget, _dj_forms.CheckboxInput | _dj_forms.RadioSelect):
                visible.field.widget.attrs['class'] = 'custom-control-input'
            else:
                visible.field.widget.attrs['class'] = 'form-control'

    @property
    def name(self) -> str:
        return self._name

    @property
    def warn_unsaved_changes(self) -> bool:
        return self._warn_unsaved_changes

    @property
    def sections(self) -> dict[str, dict[str, _typ.Iterable[_dj_forms.Field]]]:
        return self._sections


class ConfirmPasswordFormMixin:
    """Mixin for forms with a password confirmation field."""

    def clean_password_confirm(self):
        # noinspection PyUnresolvedReferences
        if not self.passwords_match():
            raise _dj_exc.ValidationError('passwords do not match', code='passwords_mismatch')

    def passwords_match(self) -> bool:
        """Check whether the passwords in the 'password' and 'password_confirm' fields match."""
        cleaned_data = getattr(self, 'cleaned_data')
        return cleaned_data['password'] == cleaned_data['password_confirm']
