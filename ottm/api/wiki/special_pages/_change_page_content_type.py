"""This module defines the user contributions special page."""
import typing as _typ

import django.contrib.auth.models as dj_auth_models
import django.forms as dj_forms

from . import Redirect, SpecialPage as _SP
from .. import constants, pages
from ... import errors
from .... import forms, models, requests


class SpecialPageChangePageContentType(_SP):
    """This special page lets users change the content type of a page.

    Args: ``/<page_name:str>``
        - ``page_name``: the name of the page.
    """

    def __init__(self):
        super().__init__(name='ChangePageContentType')

    def _process_request(self, params: requests.RequestParams, args: list[str]) -> dict[str, _typ.Any] | Redirect:
        target_page = None
        global_errors = []
        if params.post:
            form = _Form(params.post)
            if form.is_valid():
                target_page = pages.get_page(*pages.split_title(form.cleaned_data['page_name']))
                content_type = form.cleaned_data['content_type']
                try:
                    pages.set_page_content_type(params.request, params.user, target_page, content_type,
                                                form.cleaned_data['reason'])
                except errors.PageDoesNotExistError:
                    global_errors.append('page_does_not_exist')
                except errors.MissingPermissionError:
                    global_errors.append('missing_permission')
                except errors.EditSpecialPageError:
                    global_errors.append('edit_special_page')
                else:
                    return {
                        'title_key': 'title_done',
                        'title_value': target_page.full_title,
                        'target_page': target_page,
                        'content_type': content_type,
                    }
        else:
            if args:
                target_page = pages.get_page(*pages.split_title('/'.join(args)))
            if not target_page:
                form = _Form()
            else:
                if not target_page.exists:
                    global_errors.append('page_does_not_exist')
                    form = _Form(initial={'page_name': target_page.full_title})
                else:
                    form = _Form(initial={'page_name': target_page.full_title,
                                          'content_type': target_page.content_type})
        if target_page and target_page.exists:
            log_entries = target_page.pagecontenttypelog_set.reverse()
        else:
            log_entries = dj_auth_models.EmptyManager(models.PageContentLanguageLog)
        return {
            'title_key': 'title_page' if target_page else 'title',
            'title_value': target_page.full_title if target_page else None,
            'target_page': target_page,
            'form': form,
            'global_errors': global_errors,
            'log_entries': log_entries,
        }


class _Form(forms.WikiForm):
    page_name = dj_forms.CharField(
        label='page',
        max_length=200,
        min_length=1,
        required=True,
        strip=True,
        validators=[models.page_title_validator],
    )
    content_type = dj_forms.ChoiceField(
        label='content_type',
        required=True,
        choices=tuple((v, v) for v in constants.CONTENT_TYPES.values()),
    )
    reason = dj_forms.CharField(
        label='reason',
        max_length=200,
        strip=True,
        required=False,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('set_page_content_type', False, post, initial)
