"""This module defines the handler for user profile pages."""
from __future__ import annotations

import django.core.handlers.wsgi as _dj_wsgi
import django.db.models as _dj_models
import django.forms as _dj_forms
from django.http import response as _dj_response

from . import _ottm_handler, _user_page_context
from .. import forms as _forms, models as _models, requests as _requests
from ..api import auth as _auth, errors as _errors, permissions as _perms


class UserProfilePageHandler(_ottm_handler.OTTMHandler):
    """Handler for user profile pages."""

    def __init__(self, request: _dj_wsgi.WSGIRequest, username: str):
        """Create a handler for the given user’s profile page.

        :param request: Client request.
        :param username: Username of the target user.
        """
        super().__init__(request)
        self._username = username

    def handle_request(self) -> _dj_response.HttpResponse:
        target_user = _auth.get_user_from_name(self._username)
        if not target_user:
            raise _dj_response.Http404()
        match self._request_params.get.get('action'):
            case 'block':
                return self._handle_block(target_user)
            case 'mask_username':
                return self._handle_mask_username(target_user)
            case 'rename':
                return self._handle_rename(target_user)
            case 'edit_groups':
                return self._handle_edit_groups(target_user)
            case _:
                return self._handle_view_profile(target_user)

    def _handle_view_profile(self, target_user: _models.User) -> _dj_response.HttpResponse:
        title, tab_title = self.get_page_titles(page_id='user_profile', titles_args={'username': target_user.username})
        return self.render_page('ottm/user-profile/view.html', UserProfilePageContext(
            self._request_params,
            tab_title,
            title,
            target_user=target_user,
            groups=[group.label for group in target_user.get_groups()],
        ))

    def _handle_block(self, target_user: _models.User) -> _dj_response.HttpResponse:
        if not self._request_params.user.has_permission(_perms.PERM_BLOCK_USERS):
            return self.redirect('ottm:user_profile', reverse=True, username=target_user.username)

        global_errors = []
        form = BlockUserForm(initial={
            'allow_messages_on_own_user_page': True,
            'allow_editing_own_settings': True,
        })
        unblock_form = UnblockUserForm()
        if self._request_params.post:
            if self._request_params.post.get('form-name') == 'block':
                form = BlockUserForm(post=self._request_params.post)
                if form.is_valid():
                    try:
                        _auth.block_user(target_user, self._request_params.user,
                                         form.cleaned_data['allow_messages_on_own_user_page'],
                                         form.cleaned_data['allow_editing_own_settings'],
                                         form.cleaned_data['end_date'],
                                         form.cleaned_data['reason'])
                    except _errors.MissingPermissionError:
                        global_errors.append('missing_permission')
                    else:
                        return self.redirect('ottm:user_profile', reverse=True, username=target_user.username)
            else:
                unblock_form = UnblockUserForm(post=self._request_params.post)
                if unblock_form.is_valid():
                    try:
                        _auth.unblock_user(target_user, self._request_params.user, unblock_form.cleaned_data['reason'])
                    except _errors.MissingPermissionError:
                        global_errors.append('missing_permission')
                    else:
                        return self.redirect('ottm:user_profile', reverse=True, username=target_user.username)

        title, tab_title = self.get_page_titles(page_id='user_profile.block',
                                                titles_args={'username': target_user.username})
        return self.render_page(f'ottm/user-profile/block.html', UserBlockPageContext(
            self._request_params,
            tab_title,
            title,
            target_user=target_user,
            form=form,
            global_errors=global_errors,
            log_entries=_models.UserBlockLog.objects.filter(user=target_user.internal_object).reverse(),
            unblock_form=unblock_form,
        ))

    def _handle_mask_username(self, target_user: _models.User) -> _dj_response.HttpResponse:
        if not self._request_params.user.has_permission(_perms.PERM_MASK) or not target_user.is_authenticated:
            return self.redirect('ottm:user_profile', reverse=True, username=target_user.username)

        global_errors = []
        if self._request_params.post:
            form = MaskUsernameForm(post=self._request_params.post)
            if form.is_valid():
                try:
                    _auth.mask_username(target_user, self._request_params.user, mask=form.cleaned_data['mask'],
                                        reason=form.cleaned_data['reason'])
                except _errors.MissingPermissionError:
                    global_errors.append('missing_permission')
                except _errors.AnonymousMaskUsernameError:
                    global_errors.append('anonymous_user')
                else:
                    return self.redirect('ottm:user_profile', reverse=True, username=target_user.username)
        else:
            form = MaskUsernameForm(initial={
                'mask': not target_user.hide_username,
            })

        title, tab_title = self.get_page_titles(page_id='user_profile.mask_username',
                                                titles_args={'username': target_user.username})
        return self.render_page(f'ottm/user-profile/action-form.html', UserProfileActionPageContext(
            self._request_params,
            tab_title,
            title,
            target_user=target_user,
            form=form,
            global_errors=global_errors,
            log_entries=_models.UserMaskLog.objects.filter(user=target_user.internal_object).reverse(),
        ))

    def _handle_rename(self, target_user: _models.User) -> _dj_response.HttpResponse:
        pass  # TODO

    def _handle_edit_groups(self, target_user: _models.User) -> _dj_response.HttpResponse:
        if (not self._request_params.user.has_permission(_perms.PERM_EDIT_USER_GROUPS)
                or not target_user.is_authenticated):
            return self.redirect('ottm:user_profile', reverse=True, username=target_user.username)

        global_errors = []
        if self._request_params.post:
            form = EditUserGroupsForm(post=self._request_params.post)
            if form.is_valid():
                all_groups = {group.label for group in _models.UserGroup.get_assignable_groups()}
                groups = set(form.cleaned_data['groups'])
                try:
                    _auth.add_user_to_groups(target_user, *groups,
                                             performer=self._request_params.user,
                                             reason=form.cleaned_data['reason'])
                    _auth.remove_user_from_groups(target_user, *(all_groups - groups),
                                                  performer=self._request_params.user,
                                                  reason=form.cleaned_data['reason'])
                except _errors.MissingPermissionError:
                    global_errors.append('missing_permission')
                except _errors.AnonymousEditGroupsError:
                    global_errors.append('anonymous_user')
                else:
                    return self.redirect('ottm:user_profile', reverse=True, username=target_user.username)
        else:
            form = EditUserGroupsForm(initial={
                'groups': [g.label for g in target_user.get_groups()],
            })

        title, tab_title = self.get_page_titles(page_id='user_profile.edit_groups',
                                                titles_args={'username': target_user.username})
        return self.render_page(f'ottm/user-profile/action-form.html', UserProfileActionPageContext(
            self._request_params,
            tab_title,
            title,
            target_user=target_user,
            form=form,
            global_errors=global_errors,
            log_entries=_models.UserGroupLog.objects.filter(user=target_user.internal_object).reverse(),
        ))


class UserProfilePageContext(_user_page_context.UserPageContext):
    """Context class for user profile pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            target_user: _models.User,
            groups: list[str],
    ):
        """Create a page context for a user’s profile page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param target_user: User of the requested page.
        :param groups: List of the user’s group labels.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            target_user=target_user,
        )
        self._groups = groups

    @property
    def user_groups(self) -> list[str]:
        return self._groups


class UserProfileActionPageContext(_user_page_context.UserPageContext):
    """Context class for the user profile action pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            target_user: _models.User,
            form: _forms.CustomForm,
            global_errors: list[str],
            log_entries: _dj_models.QuerySet[_models.UserLog],
    ):
        """Create a page context for a user profile action page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param target_user: User of the requested page.
        :param form: The form.
        :param global_errors: Global errors.
        :param log_entries: List of related log entries.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            target_user=target_user,
        )
        self._form = form
        self._global_errors = global_errors
        self._log_entries = log_entries

    @property
    def form(self) -> _forms.CustomForm:
        return self._form

    @property
    def global_errors(self) -> list[str]:
        return self._global_errors

    @property
    def log_entries(self) -> _dj_models.QuerySet[_models.UserLog]:
        return self._log_entries


class UserBlockPageContext(UserProfileActionPageContext):
    """Context class for the user block pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            target_user: _models.User,
            form: _forms.CustomForm,
            global_errors: list[str],
            log_entries: _dj_models.QuerySet[_models.UserLog],
            unblock_form: _forms.CustomForm,
    ):
        """Create a page context for a user block page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param target_user: User of the requested page.
        :param form: The form.
        :param global_errors: Global errors.
        :param log_entries: List of related log entries.
        :param unblock_form: The unblock form.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            target_user=target_user,
            form=form,
            global_errors=global_errors,
            log_entries=log_entries,
        )
        self._unblock_form = unblock_form

    @property
    def unblock_form(self) -> _forms.CustomForm:
        return self._unblock_form


class EditUserGroupsForm(_forms.CustomForm):
    """Edit user groups form."""

    groups = _dj_forms.MultipleChoiceField(
        label='groups',
        widget=_dj_forms.CheckboxSelectMultiple(attrs={'no_translate': True}),
        choices=(),  # Set in __init__()
        required=False,
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.UserGroupLog._meta.get_field('reason').max_length,
        required=False,
        strip=True,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('edit_groups', False, post=post, initial=initial)
        self.fields['groups'].choices = tuple(
            (group.label, group.label) for group in _models.UserGroup.get_assignable_groups())


class MaskUsernameForm(_forms.CustomForm):
    """Mask username form."""

    mask = _dj_forms.BooleanField(
        label='mask',
        required=False,
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.UserMaskLog._meta.get_field('reason').max_length,
        required=False,
        strip=True,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('mask_username', False, post=post, initial=initial)


class BlockUserForm(_forms.CustomForm):
    """Block user form."""

    end_date = _dj_forms.DateField(
        label='end_date',
        widget=_dj_forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )
    allow_messages_on_own_user_page = _dj_forms.BooleanField(
        label='allow_messages_on_own_user_page',
        required=False,
    )
    allow_editing_own_settings = _dj_forms.BooleanField(
        label='allow_editing_own_settings',
        required=False,
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.UserBlockLog._meta.get_field('reason').max_length,
        required=False,
        strip=True,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('block', False, post=post, initial=initial)


class UnblockUserForm(_forms.CustomForm):
    """Unblock user form."""

    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.UserBlockLog._meta.get_field('reason').max_length,
        required=False,
        strip=True,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('unblock', False, post=post, initial=initial)
