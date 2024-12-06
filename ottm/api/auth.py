"""This module declares functions related to user authentication."""
import datetime

import django.contrib.auth as _dj_auth
import django.core.exceptions as _dj_exc
import django.core.handlers.wsgi as _dj_wsgi
import django.core.validators as _dj_valid
import django.db.transaction as _dj_db_trans

from .. import data_model as _models
from ..api import errors as _errors, groups as _groups, permissions as _perms, utils as _utils
from ..api.wiki import namespaces as _w_ns, pages as _w_pages


def log_in(request: _dj_wsgi.WSGIRequest, username: str, password: str) -> bool:
    """Log in a user.

    :param request: Client request.
    :param username: User’s username.
    :param password: User’s password.
    :return: True if the login was successful, false otherwise.
    """
    if (user := _dj_auth.authenticate(request, username=username, password=password)) is not None:
        _dj_auth.login(request, user)
        return True
    return False


def log_out(request: _dj_wsgi.WSGIRequest):
    """Log out the user associated to the given request.

    :param request: Client request.
    """
    _dj_auth.logout(request)


def get_user_from_request(request: _dj_wsgi.WSGIRequest) -> _models.User:
    """Return the user associated to the given request."""
    user = _dj_auth.get_user(request)
    if user.is_anonymous:
        return _get_or_create_anonymous_user(request)
    return _models.User(user)


def get_user_from_name(username: str) -> _models.User | None:
    """Return the user object for the given username or None if the username is not registered."""
    try:
        return _models.User(_dj_auth.get_user_model().objects.get(username=username))
    except _dj_auth.get_user_model().DoesNotExist:
        return None


@_dj_db_trans.atomic
def _get_or_create_anonymous_user(request: _dj_wsgi.WSGIRequest) -> _models.User:
    """Create a new anonymous user account for the IP address of the given request.
    If an anonymous account for the IP already exists, it is returned and no new one is created.

    :param request: Request to create the user object from.
    """
    try:
        latest_user = _models.CustomUser.objects.latest('id')
    except _models.CustomUser.DoesNotExist:
        nb = 0
    else:
        nb = latest_user.id

    ip = _get_ip(request)
    try:
        dj_user = _models.CustomUser.objects.get(ip=ip)
    except _models.CustomUser.DoesNotExist:
        # Create temporary user account
        language = _models.Language.get_default()
        dj_user = _models.CustomUser(
            username=f'Anonymous-{nb + 1}',
            ip=ip,
            preferred_language=language,
            preferred_datetime_format=language.default_datetime_format,
        )

    return _models.User(dj_user)


def _get_ip(request: _dj_wsgi.WSGIRequest) -> str:
    """Return the IP of the given request."""
    # Client’s IP address is always at the last one in HTTP_X_FORWARDED_FOR on Heroku
    # https://stackoverflow.com/questions/18264304/get-clients-real-ip-address-on-heroku#answer-18517550
    if x_forwarded_for := request.META.get('HTTP_X_FORWARDED_FOR'):
        return x_forwarded_for[-1]
    return request.META.get('REMOTE_ADDR')


@_dj_db_trans.atomic
def create_user(username: str, email: str = None, password: str = None, ignore_email: bool = False,
                is_bot: bool = False) -> _models.User:
    """Create a new user account.

    :param username: User’s username.
    :param email: User’s email address.
    :param password: User’s password.
    :param ignore_email: Whether to ignore the email address. Reserved for internal bot users.
    :param is_bot: Whether this user is a bot account.
    :return: A new user object.
    :raise InvalidUsernameError: If the username is invalid.
    :raise DuplicateUsernameError: If the username is already taken.
    """
    try:
        _models.username_validator(username)
    except _dj_exc.ValidationError as e:
        match e.code:
            case 'invalid':
                raise _errors.InvalidUsernameError(username)
            case 'duplicate':
                raise _errors.DuplicateUsernameError(username)
            case _:
                raise e

    if email and not ignore_email:
        try:
            _dj_valid.validate_email(email)
        except _dj_exc.ValidationError:
            raise _errors.InvalidEmailError(email)

    language = _models.Language.get_default()
    dj_user = _models.CustomUser.objects.create_user(
        username=username,
        email=email,
        password=password,
        preferred_language=language,
        preferred_datetime_format=language.default_datetime_format,
        is_bot=is_bot,
    )
    dj_user.save()
    dj_user.groups.add(_models.UserGroup.objects.get(label=_groups.GROUP_ALL))
    dj_user.groups.add(_models.UserGroup.objects.get(label=_groups.GROUP_USERS))
    # Add to log
    _models.UserAccountCreationLog(user=dj_user).save()

    return _models.User(dj_user)


@_dj_db_trans.atomic
def rename_user(user: _models.User, performer: _models.User, new_name: str, reason: str = None):
    """Rename a user.

    :param user: User to rename.
    :param performer: User performing the action.
    :param new_name: User’s new username.
    :param reason: Reason for the renaming.
    :raise MissingPermissionError: If the performer does not have the "rename_user" permission.
    :raise AnonymousRenameError: If the user is anonymous.
    :raise DuplicateUsernameError: If the new username is already taken.
    :raise TitleAlreadyExistsError: If the new wiki user page already exists.
    """
    if not performer.has_permission(_perms.PERM_MASK):
        raise _errors.MissingPermissionError(_perms.PERM_MASK)
    if not user.is_authenticated:
        raise _errors.AnonymousRenameError()
    if get_user_from_name(new_name):
        raise _errors.DuplicateUsernameError(new_name)
    old_name = user.username
    user.username = new_name
    user.internal_object.save()
    # Rename wiki user page
    old_user_page = _w_pages.get_page(_w_ns.NS_USER, old_name)
    if old_user_page.exists:
        try:
            _w_pages.rename_page(performer, old_user_page,
                                 _w_ns.NS_USER.get_full_page_title(new_name), leave_redirect=True, reason=reason)
        except _errors.CannotEditPageError:
            pass
    _models.UserRenameLog(
        user=user.internal_object,
        performer=performer.internal_object,
        old_username=old_name,
        new_username=new_name,
        reason=reason,
    ).save()


@_dj_db_trans.atomic
def add_user_to_groups(user: _models.User, *group_names: str, performer: _models.User = None, reason: str = None):
    """Add a user to the given groups.

    :param user: User to add to the groups.
    :param group_names: The names of the groups.
    :param performer: The user performing the action, None if internal call.
    :param reason: Reason for the group change.
    :raise MissingPermissionError: If the performer does not have the "edit_user_groups" permission.
    :raise AnonymousEditGroupsError: If the user is anonymous.
    :raise ValueError: If no group with the given name exists.
    """
    if performer:
        if not performer.has_permission(_perms.PERM_EDIT_USER_GROUPS):
            raise _errors.MissingPermissionError(_perms.PERM_EDIT_USER_GROUPS)
        if not user.is_authenticated:
            raise _errors.AnonymousEditGroupsError()
    for group_name in group_names:
        try:
            group = _models.UserGroup.objects.get(label=group_name)
        except _models.UserGroup.DoesNotExist:
            raise ValueError(f'invalid group name {group_name!r}')
        if user.is_in_group(group):
            continue
        user.internal_object.groups.add(group)
        _models.UserGroupLog(
            user=user.internal_object,
            performer=performer.internal_object if performer else None,
            joined=True,
            group=group,
            reason=reason,
        ).save()


@_dj_db_trans.atomic
def remove_user_from_groups(user: _models.User, *group_names: str, performer: _models.User = None, reason: str = None):
    """Remove a user from the given groups.

    :param user: User to remove from the groups.
    :param group_names: The names of the groups.
    :param performer: The user performing the action, None if internal call.
    :param reason: Reason for the group change.
    :raise MissingPermissionError: If the performer does not have the "edit_user_groups" permission.
    :raise AnonymousEditGroupsError: If the user is anonymous.
    :raise EditGroupsError: If either 'all' or 'users' groups are present.
    :raise ValueError: If no group with the given name exists.
    """
    if performer:
        if not performer.has_permission(_perms.PERM_EDIT_USER_GROUPS):
            raise _errors.MissingPermissionError(_perms.PERM_EDIT_USER_GROUPS)
        if not user.is_authenticated:
            raise _errors.AnonymousEditGroupsError()
        if _groups.GROUP_ALL in group_names:
            raise _errors.EditGroupsError(_groups.GROUP_ALL)
        if _groups.GROUP_USERS in group_names:
            raise _errors.EditGroupsError(_groups.GROUP_USERS)
    for group_name in group_names:
        try:
            group = _models.UserGroup.objects.get(label=group_name)
        except _models.UserGroup.DoesNotExist:
            raise ValueError(group_name)
        if not user.is_in_group(group):
            continue
        user.internal_object.groups.remove(group)
        _models.UserGroupLog(
            user=user.internal_object,
            performer=performer.internal_object if performer else None,
            joined=False,
            group=group,
            reason=reason,
        ).save()


@_dj_db_trans.atomic
def mask_username(user: _models.User, performer: _models.User, mask: bool, reason: str = None):
    """Mask/unmask the username of a user.

    :param user: The user to mask/unmask the username of.
    :param performer: User performing the action.
    :param mask: True to mask the username, false to unmask it.
    :param reason: Reason for the mask/unmask.
    :raise MissingPermissionError: If the performer does not have the "mask" permission.
    :raise AnonymousMaskUsernameError: If the user is anonymous.
    """
    if performer:
        if not performer.has_permission(_perms.PERM_MASK):
            raise _errors.MissingPermissionError(_perms.PERM_MASK)
        if not user.is_authenticated:
            raise _errors.AnonymousMaskUsernameError()
    if user.hide_username == mask:
        return
    user.hide_username = mask
    user.internal_object.save()
    _models.UserMaskLog(
        user=user.internal_object,
        performer=performer.internal_object if performer else None,
        masked=mask,
        reason=reason,
    ).save()


@_dj_db_trans.atomic
def block_user(user: _models.User, performer: _models.User, allow_messages_on_own_user_page: bool,
               allow_editing_own_settings: bool, end_date: datetime.datetime = None, reason: str = None):
    """Block the given user. Any pre-existing blocks for this user will be deleted.

    :param user: The user to block.
    :param performer: The user performing the action.
    :param allow_messages_on_own_user_page: Whether to allow the user to post messages on its own user page.
    :param allow_editing_own_settings: Whether to allow the user to edit its own settings.
    :param end_date: The date until which to block this user. None means infinite.
    :param reason: The block’s reason.
    :raise MissingPermissionError: If the performer does not have the "block_users" permission.
    :raise PastDateError: If the date is in the past.
    """
    if performer and not performer.has_permission(_perms.PERM_BLOCK_USERS):
        raise _errors.MissingPermissionError(_perms.PERM_BLOCK_USERS)
    if end_date and end_date <= _utils.now().date():
        raise _errors.PastDateError()
    for block in _models.UserBlock.objects.filter(user=user.internal_object):
        block.delete()
    _models.UserBlock(
        user=user.internal_object,
        end_date=end_date,
        allow_messages_on_own_user_page=allow_messages_on_own_user_page,
        allow_editing_own_settings=allow_editing_own_settings,
    ).save()
    _models.UserBlockLog(
        user=user.internal_object,
        performer=performer.internal_object,
        reason=reason,
        end_date=end_date,
        allow_messages_on_own_user_page=allow_messages_on_own_user_page,
        allow_editing_own_settings=allow_editing_own_settings,
        blocked=True,
    ).save()


@_dj_db_trans.atomic
def unblock_user(user: _models.User, performer: _models.User, reason: str = None):
    """Unblock the given user.

    :param user: The user to unblock.
    :param performer: The user performing the action.
    :param reason: The unblock’s reason.
    """
    if performer and not performer.has_permission(_perms.PERM_BLOCK_USERS):
        raise _errors.MissingPermissionError(_perms.PERM_BLOCK_USERS)
    for block in _models.UserBlock.objects.filter(user=user.internal_object):
        block.delete()
    _models.UserBlockLog(
        user=user.internal_object,
        performer=performer.internal_object,
        reason=reason,
        allow_messages_on_own_user_page=True,
        allow_editing_own_settings=True,
        blocked=False,
    ).save()


def user_exists(username: str) -> bool:
    """Check whether the given username exists."""
    return _dj_auth.get_user_model().objects.filter(username=username).exists()
