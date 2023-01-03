"""This module defines the subpages special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.forms as _dj_forms
import django.core.exceptions as _dj_exc

from . import _core
from .. import namespaces as _w_ns, pages as _w_pages
from ... import errors as _errors, permissions as _perms
from .... import forms as _forms, models as _models, page_handlers as _ph, requests as _requests


class RenamePageSpecialPage(_core.SpecialPage):
    """This special page lets users rename pages.

    Args: ``/<page_name:str>``
        - ``page_name``: the name of the page to rename.
    """

    def __init__(self):
        super().__init__('RenamePage', _perms.PERM_WIKI_PROTECT, accesskey='a', category=_core.Section.PAGE_OPERATIONS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        if args:
            target_page = _w_pages.get_page(*_w_pages.split_title('/'.join(args)))
        else:
            target_page = None
        user = params.user
        form = _Form(user)
        global_errors = {form.name: []}
        if params.post:
            form = _Form(user, post=params.post)
            if form.is_valid():
                target_page = _w_pages.get_page(*_w_pages.split_title(form.cleaned_data['page_name']))
                new_title = form.cleaned_data['new_title']
                leave_redirect = form.cleaned_data['leave_redirect']
                reason = form.cleaned_data['reason']
                try:
                    _w_pages.rename_page(params.user, target_page, new_title, leave_redirect, reason)
                except _errors.PageDoesNotExistError:  # Keep as the page may have been deleted right before submit
                    global_errors[form.name].append('page_does_not_exist')
                except _errors.TitleAlreadyExistsError:
                    global_errors[form.name].append('page_already_exists')
                except _errors.MissingPermissionError:
                    global_errors[form.name].append('missing_permission')
                except _errors.CannotEditPageError as e:
                    global_errors[form.name].append(
                        'cannot_edit_page' if str(e) == target_page.full_title else 'cannot_edit_target_page')
                else:
                    return _core.Redirect(
                        f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{target_page.full_title}',
                        args={'done': True}
                    )
        else:
            if target_page:
                if not target_page.exists:
                    global_errors[form.name].append('page_does_not_exist')
                form = _Form(user, initial={
                    'page_name': target_page.full_title,
                    'leave_redirect': True,
                })
        if target_page and target_page.exists:
            log_entries = target_page.pagerenamelog_set.reverse()
        else:
            log_entries = _dj_auth_models.EmptyManager(_models.PageRenameLog)
        return {
            'title_key': 'title_page' if target_page else 'title',
            'title_value': target_page.full_title if target_page else None,
            'target_page': target_page,
            'form': form,
            'global_errors': global_errors,
            'log_entries': log_entries,
            'done': params.get.get('done'),
        }


def _page_does_not_exist_validator(title: str):
    if _w_pages.get_page(*_w_pages.split_title(title)).exists:
        raise _dj_exc.ValidationError('page already exists', code='page_already_exists')


class _Form(_ph.WikiForm):
    page_name = _dj_forms.CharField(
        label='page',
        max_length=_models.Page._meta.get_field('title').max_length,
        required=True,
        strip=True,
        validators=[_models.page_title_validator, _forms.non_special_page_validator, _forms.page_exists_validator],
    )
    new_title = _dj_forms.CharField(
        label='new_title',
        max_length=_models.Page._meta.get_field('title').max_length,
        required=True,
        strip=True,
        validators=[_models.page_title_validator, _forms.non_special_page_validator, _page_does_not_exist_validator],
    )
    leave_redirect = _dj_forms.BooleanField(
        label='leave_redirect',
        required=False,
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.PageRenameLog._meta.get_field('reason').max_length,
        required=False,
        strip=True,
    )

    def __init__(self, user: _models.User, post=None, initial=None):
        super().__init__('rename_page', False, post=post, initial=initial)
        self.fields['leave_redirect'].widget.attrs['disabled'] = not user.has_permission(_perms.PERM_WIKI_DELETE)
