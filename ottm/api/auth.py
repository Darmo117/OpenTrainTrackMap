"""This module declares functions related to user authentication."""
import django.contrib.auth as dj_auth
import django.core.exceptions as dj_exc
import django.core.handlers.wsgi as dj_wsgi
import django.core.validators as dj_valid
import django.db.transaction as dj_db_trans

from .. import models
from ..api import errors, groups, permissions as _perms


def log_in(request: dj_wsgi.WSGIRequest, username: str, password: str) -> bool:
    """Log in a user.

    :param request: Client request.
    :param username: User’s username.
    :param password: User’s password.
    :return: True if the login was successful, false otherwise.
    """
    if (user := dj_auth.authenticate(request, username=username, password=password)) is not None:
        dj_auth.login(request, user)
        return True
    return False


def log_out(request: dj_wsgi.WSGIRequest):
    """Log out the user associated to the given request.

    :param request: Client request.
    """
    dj_auth.logout(request)


def get_user_from_request(request: dj_wsgi.WSGIRequest) -> models.User:
    """Return the user associated to the given request."""
    user = dj_auth.get_user(request)
    if user.is_anonymous:
        return _get_or_create_anonymous_user(request)
    return models.User(user)


def get_user_from_name(username: str) -> models.User | None:
    """Return the user object for the given username or None if the username is not registered."""
    try:
        return models.User(dj_auth.get_user_model().objects.get(username=username))
    except dj_auth.get_user_model().DoesNotExist:
        return None


@dj_db_trans.atomic
def _get_or_create_anonymous_user(request: dj_wsgi.WSGIRequest) -> models.User:
    """Create a new anonymous user account for the IP address of the given request.
    If an anonymous account for the IP already exists, it is returned and no new one is created.

    :param request: Request to create the user object from.
    """
    try:
        latest_user = models.CustomUser.objects.latest('id')
    except models.CustomUser.DoesNotExist:
        nb = 0
    else:
        nb = latest_user.id

    ip = _get_ip(request)
    try:
        dj_user = models.CustomUser.objects.get(ip=ip)
    except models.CustomUser.DoesNotExist:
        # Create temporary user account
        language = models.Language.get_default()
        dj_user = models.CustomUser(
            username=f'Anonymous-{nb + 1}',
            ip=ip,
            preferred_language=language,
            preferred_datetime_format=language.default_datetime_format,
        )

    return models.User(dj_user)


def _get_ip(request: dj_wsgi.WSGIRequest) -> str:
    """Return the IP of the given request."""
    # Client’s IP address is always at the last one in HTTP_X_FORWARDED_FOR on Heroku
    # https://stackoverflow.com/questions/18264304/get-clients-real-ip-address-on-heroku#answer-18517550
    if x_forwarded_for := request.META.get('HTTP_X_FORWARDED_FOR'):
        return x_forwarded_for[-1]
    return request.META.get('REMOTE_ADDR')


@dj_db_trans.atomic
def create_user(username: str, email: str = None, password: str = None, ignore_email: bool = False,
                is_bot: bool = False) -> models.User:
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
        models.username_validator(username)
    except dj_exc.ValidationError as e:
        match e.code:
            case 'invalid':
                raise errors.InvalidUsernameError(username)
            case 'duplicate':
                raise errors.DuplicateUsernameError(username)
            case _:
                raise e

    if email and not ignore_email:
        try:
            dj_valid.validate_email(email)
        except dj_exc.ValidationError:
            raise errors.InvalidEmailError(email)

    language = models.Language.get_default()
    dj_user = models.CustomUser.objects.create_user(
        username=username,
        email=email,
        password=password,
        preferred_language=language,
        preferred_datetime_format=language.default_datetime_format,
        is_bot=is_bot,
    )
    dj_user.save()
    dj_user.groups.add(models.UserGroup.objects.get(label=groups.GROUP_ALL))
    dj_user.groups.add(models.UserGroup.objects.get(label=groups.GROUP_USERS))
    # Add to log
    models.UserAccountCreationLog(user=dj_user).save()

    return models.User(dj_user)


@dj_db_trans.atomic
def add_user_to_groups(user: models.User, *group_names: str, performer: models.User = None, reason: str = None):
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
            raise errors.MissingPermissionError(_perms.PERM_EDIT_USER_GROUPS)
        if not user.is_authenticated:
            raise errors.AnonymousEditGroupsError()
    for group_name in group_names:
        try:
            group = models.UserGroup.objects.get(label=group_name)
        except models.UserGroup.DoesNotExist:
            raise ValueError(f'invalid group name {group_name!r}')
        if user.is_in_group(group):
            continue
        user.internal_object.groups.add(group)
        models.UserGroupLog(
            user=user.internal_object,
            performer=performer.internal_object if performer else None,
            joined=True,
            group=group,
            reason=reason,
        ).save()


@dj_db_trans.atomic
def remove_user_from_groups(user: models.User, *group_names: str, performer: models.User = None, reason: str = None):
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
            raise errors.MissingPermissionError(_perms.PERM_EDIT_USER_GROUPS)
        if not user.is_authenticated:
            raise errors.AnonymousEditGroupsError()
        if groups.GROUP_ALL in group_names:
            raise errors.EditGroupsError(groups.GROUP_ALL)
        if groups.GROUP_USERS in group_names:
            raise errors.EditGroupsError(groups.GROUP_USERS)
    for group_name in group_names:
        try:
            group = models.UserGroup.objects.get(label=group_name)
        except models.UserGroup.DoesNotExist:
            raise ValueError(group_name)
        if not user.is_in_group(group):
            continue
        user.internal_object.groups.remove(group)
        models.UserGroupLog(
            user=user.internal_object,
            performer=performer.internal_object if performer else None,
            joined=False,
            group=group,
            reason=reason,
        ).save()


def user_exists(username: str) -> bool:
    """Check whether the given username exists."""
    return dj_auth.get_user_model().objects.filter(username=username).exists()
