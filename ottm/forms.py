"""This module defines website’s forms."""
import typing as _typ

import django.core.exceptions as _dj_exc
import django.forms as _dj_forms

from .api import data_types as _data_types


def non_special_page_validator(value: str):
    from .api.wiki import namespaces as _w_ns, pages as _w_pages
    ns, _ = _w_pages.split_title(value)
    if ns == _w_ns.NS_SPECIAL:
        raise _dj_exc.ValidationError('special page', code='special_page')


def page_exists_validator(value: str):
    from .api.wiki import pages as _w_pages
    if not _w_pages.get_page(*_w_pages.split_title(value)).exists:
        raise _dj_exc.ValidationError('page does not exist', code='page_does_not_exist')


def user_exists_validator(value: str):
    from .api import auth as _auth
    if not _auth.get_user_from_name(value):
        raise _dj_exc.ValidationError('user does not exist', code='user_does_not_exist')


def user_not_anonymous_validator(value: str):
    from .api import auth as _auth
    if (user := _auth.get_user_from_name(value)) and not user.is_authenticated:
        raise _dj_exc.ValidationError('user is anonymous', code='user_anonymous')


class CustomForm(_dj_forms.Form):
    """Base class for all forms. Applies custom CSS styles to widgets."""

    def __init__(self, name: str, warn_unsaved_changes: bool, danger: bool = False,
                 fields_genders: dict[str, _data_types.UserGender] = None,
                 sections: dict[str, dict[str, list[str]]] = None, post=None, initial=None):
        super().__init__(post, initial=initial)
        self._name = name
        self._warn_unsaved_changes = warn_unsaved_changes
        self._danger = danger
        self._fields_genders = fields_genders or {}
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
    def danger(self) -> bool:
        return self._danger

    @property
    def warn_unsaved_changes(self) -> bool:
        return self._warn_unsaved_changes

    @property
    def sections(self) -> dict[str, dict[str, _typ.Iterable[_dj_forms.Field]]]:
        return self._sections

    @property
    def fields_genders(self) -> dict[str, _data_types.UserGender]:
        return self._fields_genders


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
