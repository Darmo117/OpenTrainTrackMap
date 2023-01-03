"""This module defines the user contributions special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.core.paginator as _dj_paginator
import django.db.models as _dj_models
import django.forms as _dj_forms

from . import _core
from .. import namespaces as _w_ns
from ... import auth as _auth, permissions as _perms
from .... import forms as _forms, models as _models, page_handlers as _ph, requests as _requests, settings as _settings


class ContributionsSpecialPage(_core.SpecialPage):
    """This special page lists all contributions of a specific user.

    Args: ``/<username:str>``
        - ``username``: the username of the user to display the contributions of.
    """

    def __init__(self):
        super().__init__('Contributions', accesskey='o', category=_core.Section.USERS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        user = _auth.get_user_from_request(params.request)
        language = params.ui_language
        if args:
            target_user = _auth.get_user_from_name(args[0])
        else:
            target_user = None
        contributions = _dj_auth_models.EmptyManager(_models.PageRevision)
        form = _Form(language)
        global_errors = {form.name: []}
        if params.POST:
            form = _Form(language, post=params.POST)
            if form.is_valid():
                if (not form.cleaned_data['start_date'] or not form.cleaned_data['end_date']
                        or form.cleaned_data['start_date'] <= form.cleaned_data['end_date']):
                    return _core.Redirect(
                        f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{form.cleaned_data["username"]}',
                        args={
                            'namespace': form.cleaned_data['namespace'],
                            'invert_selection': form.cleaned_data['invert_selection'],
                            'hidden_revisions_only': form.cleaned_data['hidden_revisions_only'],
                            'latest_revisions_only': form.cleaned_data['latest_revisions_only'],
                            'page_creations_only': form.cleaned_data['page_creations_only'],
                            'mask_minor_edits': form.cleaned_data['mask_minor_edits'],
                            'start_date': form.cleaned_data['start_date'],
                            'end_date': form.cleaned_data['end_date'],
                        }
                    )
                global_errors[form.name].append('invalid_dates')
        elif args:
            kwargs = {k: v for k, v in params.GET.items()}
            if not target_user:
                kwargs['username'] = args[0]
            else:
                kwargs['username'] = target_user.username
            form = _Form(language, post=kwargs)
            query_set = target_user.internal_object.pagerevision_set
            if user.has_permission(_perms.PERM_MASK):
                contributions = query_set.all()
            else:
                contributions = query_set.filter(hidden=False)
            if form.is_valid():
                ns_id = form.cleaned_data['namespace']
                if ns_id != '':
                    ns = _dj_models.Q(page__namespace_id=int(ns_id))
                    if form.cleaned_data['invert_selection']:
                        ns = ~ns
                    contributions = contributions.filter(ns)
                if form.cleaned_data['hidden_revisions_only']:
                    contributions = contributions.filter(hidden=True)
                if form.cleaned_data['page_creations_only']:
                    contributions = contributions.filter(page_creation=True)
                if form.cleaned_data['mask_minor_edits']:
                    contributions = contributions.filter(is_minor=False)
                if form.cleaned_data['latest_revisions_only']:
                    # Solution from https://stackoverflow.com/a/19930802/3779986
                    # May be very slow if there are a lot of revisions/pages
                    contributions = contributions.annotate(max_date=_dj_models.Max('page__revisions__date')) \
                        .filter(date=_dj_models.F('max_date'))
                    # TODO try this with postgres (from https://stackoverflow.com/a/19924129/3779986):
                    #  contributions = contributions.order_by('page__id', '-date').distinct('page__id')
                if start_date := form.cleaned_data['start_date']:
                    contributions = contributions.filter(date__gte=start_date)
                if end_date := form.cleaned_data['end_date']:
                    contributions = contributions.filter(date__lte=end_date)
        paginator = _dj_paginator.Paginator(contributions.reverse(), params.results_per_page)
        return {
            'title_key': 'title_user' if target_user else 'title',
            'title_value': target_user.username if target_user else None,
            'target_user': target_user,
            'contributions': paginator,
            'form': form,
            'max_page_index': paginator.num_pages,
            'global_errors': global_errors,
        }


class _Form(_ph.WikiForm):
    username = _dj_forms.CharField(
        label='username',
        max_length=_dj_auth_models.AbstractUser._meta.get_field('username').max_length,
        required=True,
        strip=True,
        validators=[_models.username_validator, _forms.user_exists_validator],
    )
    namespace = _dj_forms.ChoiceField(
        label='namespace',
        choices=(),  # Set in __init__
        required=False,
    )
    invert_selection = _dj_forms.BooleanField(
        label='invert_selection',
        required=False,
        help_text=True,
    )
    hidden_revisions_only = _dj_forms.BooleanField(
        label='hidden_revisions_only',
        required=False,
    )
    latest_revisions_only = _dj_forms.BooleanField(
        label='last_revisions_only',
        required=False,
    )
    page_creations_only = _dj_forms.BooleanField(
        label='page_creations_only',
        required=False,
    )
    mask_minor_edits = _dj_forms.BooleanField(
        label='mask_minor_edits',
        required=False,
    )
    start_date = _dj_forms.DateField(
        label='start_date',
        widget=_dj_forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )
    end_date = _dj_forms.DateField(
        label='end_date',
        widget=_dj_forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )

    def __init__(self, language: _settings.UILanguage, post=None, initial=None):
        super().__init__('filter', False, post=post, initial=initial)
        self.fields['namespace'].choices = tuple(
            [('', language.translate('wiki.special_page.Contributions.form.filter.namespace.all'))] +
            [(str(ns_id), ns.get_display_name(language)) for ns_id, ns in _w_ns.NAMESPACE_IDS.items()]
        )
