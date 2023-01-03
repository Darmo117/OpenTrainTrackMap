"""This module defines the user mute special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.forms as _dj_forms

from . import _core
from .. import namespaces as _w_ns
from ... import auth as _auth, data_types as _data_types
from .... import forms as _forms, models as _models, page_handlers as _ph, requests as _requests


class MuteSpecialPage(_core.SpecialPage):
    """This special page lets users mute other users.

    Args: ``/<username:str>``
        - ``username``: the username of the user to mute.
    """

    def __init__(self):
        super().__init__('Mute', category=_core.Section.USERS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        user = _auth.get_user_from_request(params.request)
        if args:
            target_user = _auth.get_user_from_name(args[0])
        else:
            target_user = None
        form = _Form(_data_types.GENDER_N)
        global_errors = {form.name: []}
        if params.POST:
            form = _Form(_data_types.GENDER_N, post=params.POST)
            if form.is_valid():
                target_user = _auth.get_user_from_name(form.cleaned_data['username'])
                username = target_user.username
                if user.is_authenticated:
                    email_bl = user.email_user_blacklist
                    if form.cleaned_data['mute_emails']:
                        if username not in email_bl:
                            email_bl.append(username)
                    elif username in email_bl:
                        email_bl.remove(username)
                    user.email_user_blacklist = email_bl
                    notif_bl = user.user_notification_blacklist
                    if form.cleaned_data['mute_notifications']:
                        if username not in notif_bl:
                            notif_bl.append(username)
                    elif username in notif_bl:
                        notif_bl.remove(username)
                    user.user_notification_blacklist = notif_bl
                    user.internal_object.save()
                    return _core.Redirect(
                        f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{form.cleaned_data["username"]}',
                        args={'done': True}
                    )
                else:
                    global_errors[form.name].append('anonymous_user')
        elif args:
            if not target_user:
                global_errors[form.name].append('user_does_not_exist')
                form = _Form(_data_types.GENDER_N, initial={'username': args[0]})
            else:
                form = _Form(target_user.gender, initial={
                    'username': target_user.username,
                    'mute_emails': target_user.username in user.email_user_blacklist,
                    'mute_notifications': target_user.username in user.user_notification_blacklist,
                })
        return {
            'title_key': 'title_user' if target_user else 'title',
            'title_value': target_user.username if target_user else None,
            'target_user': target_user,
            'form': form,
            'global_errors': global_errors,
            'done': params.GET.get('done'),
        }


class _Form(_ph.WikiForm):
    username = _dj_forms.CharField(
        label='username',
        max_length=_dj_auth_models.AbstractUser._meta.get_field('username').max_length,
        required=True,
        strip=True,
        validators=[_models.username_validator, _forms.user_exists_validator],
    )
    mute_emails = _dj_forms.BooleanField(
        label='mute_emails',
        required=False,
    )
    mute_notifications = _dj_forms.BooleanField(
        label='mute_notifications',
        required=False,
    )

    def __init__(self, user_gender: _data_types.UserGender, post=None, initial=None):
        super().__init__('mute_user', False, fields_genders={
            'username': user_gender,
            'mute_emails': user_gender,
            'mute_notifications': user_gender,
        }, post=post, initial=initial)
