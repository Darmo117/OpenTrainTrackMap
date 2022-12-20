"""This module defines the handler for user profile pages."""
from __future__ import annotations

import django.core.handlers.wsgi as _dj_wsgi
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
        pass

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
                except _errors.AnonymousEditGroupsError:
                    global_errors.append('anonymous_user')
                else:
                    return self.redirect('ottm:user_profile', reverse=True, username=target_user.username)
        else:
            form = MaskUsernameForm(initial={
                'mask': not target_user.hide_username,
            })

        title, tab_title = self.get_page_titles(page_id='user_profile.mask_username',
                                                titles_args={'username': target_user.username})
        return self.render_page(f'ottm/user-profile/action-form.html', MaskUsernamePageContext(
            self._request_params,
            tab_title,
            title,
            target_user=target_user,
            form=form,
            global_errors=global_errors,
        ))

    def _handle_rename(self, target_user: _models.User) -> _dj_response.HttpResponse:
        pass

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
        return self.render_page(f'ottm/user-profile/action-form.html', EditUserGroupsPageContext(
            self._request_params,
            tab_title,
            title,
            target_user=target_user,
            form=form,
            global_errors=global_errors,
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


class EditUserGroupsPageContext(_user_page_context.UserPageContext):
    """Context class for the edit user groups pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            target_user: _models.User,
            form: EditUserGroupsForm,
            global_errors: list[str],
    ):
        """Create a page context for the edit user groups page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param target_user: User of the requested page.
        :param form: The form.
        :param global_errors: Global errors.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            target_user=target_user,
        )
        self._form = form
        self._global_errors = global_errors

    @property
    def form(self) -> EditUserGroupsForm:
        return self._form

    @property
    def global_errors(self) -> list[str]:
        return self._global_errors


class EditUserGroupsForm(_forms.CustomForm):
    groups = _dj_forms.MultipleChoiceField(
        label='groups',
        widget=_dj_forms.CheckboxSelectMultiple(),
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


class MaskUsernamePageContext(_user_page_context.UserPageContext):
    """Context class for the mask username pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            target_user: _models.User,
            form: MaskUsernameForm,
            global_errors: list[str],
    ):
        """Create a page context for the mask username page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param target_user: User of the requested page.
        :param form: The form.
        :param global_errors: Global errors.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            target_user=target_user,
        )
        self._form = form
        self._global_errors = global_errors

    @property
    def form(self) -> MaskUsernameForm:
        return self._form

    @property
    def global_errors(self) -> list[str]:
        return self._global_errors


class MaskUsernameForm(_forms.CustomForm):
    mask = _dj_forms.BooleanField(
        label='mask',
        required=False,
    )
    reason = _dj_forms.CharField(
        label='reason',
        max_length=_models.UserGroupLog._meta.get_field('reason').max_length,
        required=False,
        strip=True,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('mask_username', False, post=post, initial=initial)
