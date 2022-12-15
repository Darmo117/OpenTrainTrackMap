import typing as _typ

from .. import forms as _forms


class WikiForm(_forms.CustomForm):
    """Base class for wiki forms."""

    def __init__(self, name: str, warn_unsaved_changes: bool, post=None, initial: dict[str, _typ.Any] = None):
        """Create a wiki form.

        :param name: Form’s name.
        :param warn_unsaved_changes: Whether to display a warning whenever a user quits
            the page without submitting this form.
        :param post: A POST dict to populate this form.
        :param initial: A dict object of initial field values.
        """
        super().__init__(name, warn_unsaved_changes, post, initial=initial)
        for field_name, field in self.fields.items():
            field.widget.attrs['id'] = f'wiki-{name.replace("_", "-")}-form-{field_name.replace("_", "-")}'
