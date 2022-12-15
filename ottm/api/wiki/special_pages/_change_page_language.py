"""This module defines the user contributions special page."""
import typing as _typ

import django.contrib.auth.models as dj_auth_models
import django.forms as dj_forms

from . import Redirect, SpecialPage as _SP
from .. import pages
from ... import errors
from .... import forms, models, requests, settings


class ChangePageLanguageSpecialPage(_SP):
    """This special page lets users change the content language of a page.

    Args: ``/<page_name:str>``
        - ``page_name``: the name of the page.
    """

    def __init__(self):
        super().__init__(name='ChangePageLanguage')

    def _process_request(self, params: requests.RequestParams, args: list[str]) -> dict[str, _typ.Any] | Redirect:
        target_page = None
        global_errors = []
        if params.post:
            form = _Form(params.post)
            if form.is_valid():
                target_page = pages.get_page(*pages.split_title(form.cleaned_data['page_name']))
                content_language = settings.LANGUAGES[form.cleaned_data['content_language']]
                try:
                    done = pages.set_page_content_language(params.request, params.user, target_page, content_language,
                                                           form.cleaned_data['reason'])
                except errors.PageDoesNotExistError:
                    global_errors.append('page_does_not_exist')
                except errors.MissingPermissionError:
                    global_errors.append('missing_permission')
                except errors.EditSpecialPageError:
                    global_errors.append('edit_special_page')
                else:
                    if done:
                        return {
                            'title_key': 'title_done',
                            'title_value': target_page.full_title,
                            'target_page': target_page,
                            'content_language': content_language,
                        }
                    else:
                        global_errors.append('no_changes')
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
                                          'content_language': target_page.content_language.code})
        if target_page and target_page.exists:
            log_entries = target_page.pagecontentlanguagelog_set.reverse()
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
    content_language = dj_forms.ChoiceField(
        label='content_language',
        required=True,
        choices=()  # Set in __init__()
    )
    reason = dj_forms.CharField(
        label='reason',
        max_length=200,
        strip=True,
        required=False
    )

    def __init__(self, post=None, initial=None):
        super().__init__('set_page_language', False, post, initial)
        self.fields['content_language'].choices = tuple(
            (language.code, language.name) for language in models.Language.objects.order_by('name'))
