"""This module defines website’s forms."""
import django.core.exceptions as _dj_exc
import django.forms as _dj_forms


class CustomForm(_dj_forms.Form):
    """Base class for all forms. Applies custom CSS styles to widgets."""

    def __init__(self, name: str, warn_unsaved_changes: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = name
        self._warn_unsaved_changes = warn_unsaved_changes
        for field_name, field in self.fields.items():
            field.widget.attrs['id'] = f'{name.replace("_", "-")}-form-{field_name.replace("_", "-")}'
        for visible in self.visible_fields():
            if isinstance(visible.field.widget, _dj_forms.CheckboxInput):
                visible.field.widget.attrs['class'] = 'form-check-input'
            else:
                visible.field.widget.attrs['class'] = 'form-control'

    @property
    def name(self) -> str:
        return self._name

    @property
    def warn_unsaved_changes(self) -> bool:
        return self._warn_unsaved_changes


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
