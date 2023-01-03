"""This module defines the page deletion special page."""
import typing as _typ

import django.forms as _dj_forms
import django.core.paginator as _dj_paginator

from . import _core
from .. import namespaces as _w_ns, pages as _w_pages
from ... import errors as _errors, permissions as _perms
from .... import models as _models, page_handlers as _ph, requests as _requests


class MaskRevisionsSpecialPage(_core.SpecialPage):
    """This special page lets users mask/unmask page revisions."""

    def __init__(self):
        super().__init__('MaskRevisions', _perms.PERM_MASK, category=_core.Section.PAGE_OPERATIONS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        revision_ids = sorted(int(revid) for revid in args if revid.isascii() and revid.isnumeric())
        revisions = _models.PageRevision.objects.filter(id__in=revision_ids)
        form = _Form(initial={'action': _models.PageRevisionMaskLog.MASK_FULLY})
        global_errors = {form.name: []}
        if params.post:
            form = _Form(post=params.post)
            if form.is_valid():
                try:
                    _w_pages.change_revisions_visibility(
                        params.user,
                        [r.id for r in revisions],
                        form.cleaned_data['action'],
                        form.cleaned_data['reason']
                    )
                except _errors.NoRevisionsError:
                    global_errors[form.name].append('no_revisions')
                except _errors.CannotMaskLastRevisionError:
                    global_errors[form.name].append('cannot_mask_last_revision')
                except _errors.PageRevisionDoesNotExistError:
                    global_errors[form.name].append('revision_does_not_exist')
                except _errors.MissingPermissionError:
                    global_errors[form.name].append('missing_permission')
                except _errors.CannotEditPageError:
                    global_errors[form.name].append('cannot_edit_page')
                else:
                    return _core.Redirect(
                        f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{"/".join(args)}',
                        args={'done': True}
                    )
        return {
            'title_key': 'title',
            'title_value': None,
            'form': form,
            'global_errors': global_errors,
            'revisions': _dj_paginator.Paginator(revisions, params.results_per_page),
            'log_entries': _models.PageRevisionMaskLog.objects.filter(revision_id__in=revision_ids).reverse(),
            'done': params.get.get('done'),
        }


class _Form(_ph.WikiForm):
    action = _dj_forms.ChoiceField(
        label='action',
        widget=_dj_forms.RadioSelect(),
        choices=(
            (_models.PageRevisionMaskLog.MASK_FULLY, _models.PageRevisionMaskLog.MASK_FULLY),
            (_models.PageRevisionMaskLog.MASK_COMMENTS_ONLY, _models.PageRevisionMaskLog.MASK_COMMENTS_ONLY),
            (_models.PageRevisionMaskLog.UNMASK_ALL, _models.PageRevisionMaskLog.UNMASK_ALL),
            (_models.PageRevisionMaskLog.UNMASK_ALL_BUT_COMMENTS, _models.PageRevisionMaskLog.UNMASK_ALL_BUT_COMMENTS),
        ),
        required=False
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.PageRevisionMaskLog._meta.get_field('reason').max_length,
        strip=True,
        required=False
    )

    def __init__(self, post=None, initial=None):
        super().__init__('change_visibility', False, danger=True, post=post, initial=initial)
