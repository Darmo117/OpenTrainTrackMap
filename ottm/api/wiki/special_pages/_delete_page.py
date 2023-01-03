"""This module defines the page deletion special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.forms as _dj_forms

from . import _core
from .. import namespaces as _w_ns, pages as _w_pages
from ... import errors as _errors, permissions as _perms
from .... import forms as _forms, models as _models, page_handlers as _ph, requests as _requests


class DeletePageSpecialPage(_core.SpecialPage):
    """This special page lets users delete a page.

    Args: ``/<page_name:str>``
        - ``page_name``: the name of the page.
    """

    def __init__(self):
        super().__init__('DeletePage', _perms.PERM_WIKI_DELETE, accesskey='d', category=_core.Section.PAGE_OPERATIONS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        target_page = None
        form = _Form()
        global_errors = {form.name: []}
        if params.post:
            form = _Form(params.post)
            if form.is_valid():
                target_page = _w_pages.get_page(*_w_pages.split_title(form.cleaned_data['page_name']))
                try:
                    _w_pages.delete_page(params.user, target_page, form.cleaned_data['reason'])
                except _errors.PageDoesNotExistError:  # Keep as the page may have been deleted right before submit
                    global_errors[form.name].append('page_does_not_exist')
                except _errors.MissingPermissionError:
                    global_errors[form.name].append('missing_permission')
                except _errors.CannotEditPageError:
                    global_errors[form.name].append('cannot_edit_page')
                else:
                    return _core.Redirect(
                        f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{target_page.full_title}',
                        args={'done': True}
                    )
        else:
            if args:
                target_page = _w_pages.get_page(*_w_pages.split_title('/'.join(args)))
            if target_page:
                if not target_page.exists:
                    global_errors[form.name].append('page_does_not_exist')
                form = _Form(initial={'page_name': target_page.full_title})
        if target_page and target_page.exists:
            log_entries = target_page.pagedeletionlog_set.reverse()
        else:
            log_entries = _dj_auth_models.EmptyManager(_models.PageDeletionLog)
        return {
            'title_key': 'title_page' if target_page else 'title',
            'title_value': target_page.full_title if target_page else None,
            'target_page': target_page,
            'form': form,
            'global_errors': global_errors,
            'log_entries': log_entries,
            'revisions_nb': target_page.revisions.count() if target_page and target_page.exists else 0,
            'linked_pages': target_page.get_linked_pages() if target_page else None,
            'done': params.get.get('done'),
        }


class _Form(_ph.WikiForm):
    page_name = _dj_forms.CharField(
        label='page',
        max_length=_models.Page._meta.get_field('title').max_length,
        required=True,
        strip=True,
        validators=[_models.page_title_validator, _forms.non_special_page_validator, _forms.page_exists_validator],
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.PageContentTypeLog._meta.get_field('reason').max_length,
        strip=True,
        required=False
    )

    def __init__(self, post=None, initial=None):
        super().__init__('delete', False, danger=True, post=post, initial=initial)
