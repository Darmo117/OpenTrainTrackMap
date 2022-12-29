import typing as _typ

from .. import forms as _forms
from ..api import data_types as _data_types


class WikiForm(_forms.CustomForm):
    """Base class for wiki forms."""

    def __init__(self, name: str, warn_unsaved_changes: bool, danger: bool = False,
                 fields_genders: dict[str, _data_types.UserGender] = None,
                 post=None, initial: dict[str, _typ.Any] = None):
        """Create a wiki form.

        :param name: Form’s name.
        :param warn_unsaved_changes: Whether to display a warning whenever a user quits
            the page without submitting this form.
        :param danger: Whether to display the submit button with the danger flavour.
        :param fields_genders: Dict that indicates which gender to apply to the translation of which fields.
        :param post: A POST dict to populate this form.
        :param initial: A dict object of initial field values.
        """
        super().__init__(name, warn_unsaved_changes, danger=danger, fields_genders=fields_genders,
                         post=post, initial=initial)
        for field_name, field in self.fields.items():
            field.widget.attrs['id'] = f'wiki-{name.replace("_", "-")}-form-{field_name.replace("_", "-")}'
