"""This module defines the user contributions special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.forms as _dj_forms

from . import _core
from .. import constants as _constants, pages as _pages
from ... import errors as _errors
from .... import forms as _forms, models as _models, requests as _requests


class ChangePageContentTypeSpecialPage(_core.SpecialPage):
    """This special page lets users change the content type of a page.

    Args: ``/<page_name:str>``
        - ``page_name``: the name of the page.
    """

    def __init__(self):
        super().__init__('ChangePageContentType', category=_core.Section.OTHER)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        target_page = None
        global_errors = []
        if params.post:
            form = _Form(params.post)
            if form.is_valid():
                target_page = _pages.get_page(*_pages.split_title(form.cleaned_data['page_name']))
                content_type = form.cleaned_data['content_type']
                try:
                    done = _pages.set_page_content_type(params.request, params.user, target_page, content_type,
                                                        form.cleaned_data['reason'])
                except _errors.PageDoesNotExistError:
                    global_errors.append('page_does_not_exist')
                except _errors.MissingPermissionError:
                    global_errors.append('missing_permission')
                except _errors.EditSpecialPageError:
                    global_errors.append('edit_special_page')
                else:
                    if done:
                        return {
                            'title_key': 'title_done',
                            'title_value': target_page.full_title,
                            'target_page': target_page,
                            'content_type': content_type,
                        }
                    else:
                        global_errors.append('no_changes')
        else:
            if args:
                target_page = _pages.get_page(*_pages.split_title('/'.join(args)))
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
            log_entries = _dj_auth_models.EmptyManager(_models.PageContentLanguageLog)
        return {
            'title_key': 'title_page' if target_page else 'title',
            'title_value': target_page.full_title if target_page else None,
            'target_page': target_page,
            'form': form,
            'global_errors': global_errors,
            'log_entries': log_entries,
        }


class _Form(_forms.WikiForm):
    page_name = _dj_forms.CharField(
        label='page',
        max_length=200,
        min_length=1,
        required=True,
        strip=True,
        validators=[_models.page_title_validator],
    )
    content_type = _dj_forms.ChoiceField(
        label='content_type',
        required=True,
        choices=tuple((v, v) for v in _constants.CONTENT_TYPES.values()),
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=200,
        strip=True,
        required=False,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('set_page_content_type', False, post, initial)
