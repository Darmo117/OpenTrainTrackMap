"""This module defines the user contributions special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.forms as _dj_forms

from . import _core
from .. import namespaces as _w_ns, pages as _w_pages
from ... import errors as _errors
from .... import forms as _forms, data_model as _models, page_handlers as _ph, requests as _requests, \
    settings as _settings


class ChangePageLanguageSpecialPage(_core.SpecialPage):
    """This special page lets users change the content language of a page.

    Args: ``/<page_name:str>``
        - ``page_name``: the name of the page.
    """

    def __init__(self):
        super().__init__('ChangePageLanguage', category=_core.Section.PAGE_OPERATIONS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        if args:
            target_page = _w_pages.get_page(*_w_pages.split_title('/'.join(args)))
        else:
            target_page = None
        form = _Form()
        global_errors = {form.name: []}
        if params.POST:
            form = _Form(post=params.POST)
            if form.is_valid():
                target_page = _w_pages.get_page(*_w_pages.split_title(form.cleaned_data['page_name']))
                content_language = _settings.LANGUAGES[form.cleaned_data['content_language']]
                try:
                    done = _w_pages.set_page_content_language(params.user, target_page, content_language,
                                                              form.cleaned_data['reason'])
                except _errors.PageDoesNotExistError:  # Keep as the page may have been deleted right before submit
                    global_errors[form.name].append('page_does_not_exist')
                except _errors.CannotEditPageError:
                    global_errors[form.name].append('cannot_edit_page')
                else:
                    if done:
                        return _core.Redirect(
                            f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{target_page.full_title}',
                            args={'done': True}
                        )
        else:
            if target_page:
                if not target_page.exists:
                    global_errors[form.name].append('page_does_not_exist')
                    form = _Form(initial={'page_name': target_page.full_title})
                else:
                    form = _Form(initial={'page_name': target_page.full_title,
                                          'content_language': target_page.content_language.code})
        if target_page and target_page.exists:
            log_entries = target_page.pagecontentlanguagelog_set.reverse()
        else:
            log_entries = _dj_auth_models.EmptyManager(_models.PageContentLanguageLog)
        return {
            'title_key': 'title_page' if target_page else 'title',
            'title_value': target_page.full_title if target_page else None,
            'target_page': target_page,
            'form': form,
            'global_errors': global_errors,
            'log_entries': log_entries,
            'done': params.GET.get('done'),
        }


class _Form(_ph.WikiForm):
    page_name = _dj_forms.CharField(
        label='page',
        max_length=_models.Page._meta.get_field('title').max_length,
        required=True,
        strip=True,
        validators=[_models.page_title_validator, _forms.non_special_page_validator, _forms.page_exists_validator],
    )
    content_language = _dj_forms.ChoiceField(
        label='content_language',
        required=True,
        choices=()  # Set in __init__()
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.PageContentLanguageLog._meta.get_field('reason').max_length,
        strip=True,
        required=False
    )

    def __init__(self, post=None, initial=None):
        super().__init__('set_page_language', False, post=post, initial=initial)
        self.fields['content_language'].choices = tuple(
            (language.code, language.name) for language in _models.Language.objects.order_by('name'))
