"""This module defines the handler for user settings pages."""
from __future__ import annotations

import django.contrib.auth.models as _dj_auth
import django.core.validators as _dj_valid
import django.forms as _dj_forms
from django.http import response as _dj_response

from . import _ottm_handler, _user_page_context
from .. import forms as _forms, models as _models, requests as _requests
from ..api import data_types as _dt, timezones as _tz, utils as _utils
from ..api.wiki import constants as _const, search_engine as _se, notifications as _notif


class UserSettingsPageHandler(_ottm_handler.OTTMHandler):
    """Handler for user settings pages."""

    def handle_request(self) -> _dj_response.HttpResponse:
        if not self._request_params.user.is_authenticated:
            return self.redirect('ottm:map', reverse=True)

        user = self._request_params.user
        title, tab_title = self.get_page_titles(page_id='user_settings')
        form = UserSettingsForm(user=user)
        return self.render_page(f'ottm/user-settings.html', UserSettingsPageContext(
            self._request_params,
            title,
            tab_title,
            target_user=self._request_params.user,
            form=form,
        ))


class UserSettingsForm(_forms.CustomForm, _forms.ConfirmPasswordFormMixin):
    """User settings form."""

    password = _dj_forms.CharField(
        label='password',
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        widget=_dj_forms.PasswordInput(),
        required=False,
        help_text=True,
    )
    password_confirm = _dj_forms.CharField(
        label='password_confirm',
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        widget=_dj_forms.PasswordInput(),
        required=False,
    )
    gender = _dj_forms.ChoiceField(
        label='gender',
        widget=_dj_forms.RadioSelect(),
        required=True,
        choices=tuple((gender.label, gender.i18n_label) for gender in _dt.GENDERS.values()),
        help_text=True,
    )
    prefered_language = _dj_forms.ChoiceField(
        label='prefered_language',
        required=True,
        choices=(),  # Set in __init__
    )
    email = _dj_forms.CharField(
        label='email',
        widget=_dj_forms.EmailInput(),
        validators=[_dj_valid.validate_email],
        required=True,
        help_text=True,
    )
    users_can_send_emails = _dj_forms.BooleanField(
        label='users_can_send_emails',
        required=False,
    )
    new_users_can_send_emails = _dj_forms.BooleanField(
        label='new_users_can_send_emails',
        required=False,
    )
    send_copy_of_sent_emails = _dj_forms.BooleanField(
        label='send_copy_of_sent_emails',
        required=False,
    )
    email_user_blacklist = _dj_forms.CharField(
        label='email_user_blacklist',
        widget=_dj_forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text=True,
    )
    dark_mode = _dj_forms.BooleanField(
        label='dark_mode',
        required=False,
    )
    prefered_datetime_format = _dj_forms.ChoiceField(
        label='prefered_datetime_format',
        required=True,
        choices=(),  # Set in __init__()
    )
    prefered_timezone = _dj_forms.ChoiceField(
        label='prefered_timezone',
        required=True,
        choices=((tz, tz) for tz in _tz.TIMEZONES),  # Set in __init__()
    )
    max_file_preview_size = _dj_forms.ChoiceField(
        label='max_file_preview_size',
        required=True,
        choices=tuple((f'{n1},{n2}', f'{n1}×{n2}px') for n1, n2 in _const.FILE_PREVIEW_SIZES),
    )
    thumbnails_size = _dj_forms.IntegerField(
        label='thumbnails_size',
        required=True,
        validators=[_models.thumbnail_size_validator],
        min_value=100,
        max_value=600,
    )
    show_page_content_in_diffs = _dj_forms.BooleanField(
        label='show_page_content_in_diffs',
        required=False,
    )
    show_diff_after_revert = _dj_forms.BooleanField(
        label='show_diff_after_revert',
        required=False,
    )
    show_hidden_categories = _dj_forms.BooleanField(
        label='show_hidden_categories',
        required=False,
    )
    ask_revert_confirmation = _dj_forms.BooleanField(
        label='ask_revert_confirmation',
        required=False,
    )
    mark_all_wiki_edits_as_minor = _dj_forms.BooleanField(
        label='mark_all_wiki_edits_as_minor',
        required=False,
    )
    warn_when_no_wiki_edit_comment = _dj_forms.BooleanField(
        label='warn_when_no_wiki_edit_comment',
        required=False,
    )
    warn_when_wiki_edit_not_published = _dj_forms.BooleanField(
        label='warn_when_wiki_edit_not_published',
        required=False,
    )
    show_preview_above_edit_form = _dj_forms.BooleanField(
        label='show_preview_above_edit_form',
        required=False,
    )
    show_preview_without_reload = _dj_forms.BooleanField(
        label='show_preview_without_reload',
        required=False,
    )
    default_days_nb_in_wiki_edit_lists = _dj_forms.IntegerField(
        label='default_days_nb_in_wiki_edit_lists',
        required=True,
        validators=[_models.days_nb_rc_fl_logs_validator],
        help_text=True,
        min_value=1,
        max_value=30,
    )
    default_edits_nb_in_wiki_edit_lists = _dj_forms.IntegerField(
        label='default_edits_nb_in_wiki_edit_lists',
        required=True,
        validators=[_models.edits_nb_rc_fl_logs_validator],
        help_text=True,
        min_value=1,
        max_value=1000,
    )
    group_edits_per_page = _dj_forms.BooleanField(
        label='group_edits_per_page',
        required=False,
    )
    mask_wiki_minor_edits = _dj_forms.BooleanField(
        label='mask_wiki_minor_edits',
        required=False,
    )
    mask_wiki_bot_edits = _dj_forms.BooleanField(
        label='mask_wiki_bot_edits',
        required=False,
    )
    mask_wiki_own_edits = _dj_forms.BooleanField(
        label='mask_wiki_own_edits',
        required=False,
    )
    mask_wiki_anonymous_edits = _dj_forms.BooleanField(
        label='mask_wiki_anonymous_edits',
        required=False,
    )
    mask_wiki_authenticated_edits = _dj_forms.BooleanField(
        label='mask_wiki_authenticated_edits',
        required=False,
    )
    mask_wiki_categorization_edits = _dj_forms.BooleanField(
        label='mask_wiki_categorization_edits',
        required=False,
    )
    mask_wiki_patrolled_edits = _dj_forms.BooleanField(
        label='mask_wiki_patrolled_edits',
        required=False,
    )
    add_created_pages_to_follow_list = _dj_forms.BooleanField(
        label='add_created_pages_to_follow_list',
        required=False,
    )
    add_modified_pages_to_follow_list = _dj_forms.BooleanField(
        label='add_modified_pages_to_follow_list',
        required=False,
    )
    add_renamed_pages_to_follow_list = _dj_forms.BooleanField(
        label='add_renamed_pages_to_follow_list',
        required=False,
    )
    add_deleted_pages_to_follow_list = _dj_forms.BooleanField(
        label='add_deleted_pages_to_follow_list',
        required=False,
    )
    add_reverted_pages_to_follow_list = _dj_forms.BooleanField(
        label='add_reverted_pages_to_follow_list',
        required=False,
    )
    add_created_topics_to_follow_list = _dj_forms.BooleanField(
        label='add_created_topics_to_follow_list',
        required=False,
    )
    add_replied_to_topics_to_follow_list = _dj_forms.BooleanField(
        label='add_replied_to_topics_to_follow_list',
        required=False,
    )
    search_default_results_nb = _dj_forms.IntegerField(
        label='search_default_results_nb',
        required=True,
        validators=[_models.search_results_nb_validator],
        help_text=True,
        min_value=1,
        max_value=50,
    )
    search_mode = _dj_forms.ChoiceField(
        label='search_mode',
        widget=_dj_forms.RadioSelect(),
        required=True,
        choices=tuple((sm.value, sm.value) for sm in _se.SearchMode),
        help_text=True,
    )
    email_update_notification_frequency = _dj_forms.ChoiceField(
        label='email_update_notification_frequency',
        widget=_dj_forms.RadioSelect(),
        required=True,
        choices=tuple((nef.value, nef.value) for nef in _notif.NotificationEmailFrequency),
    )
    html_email_updates = _dj_forms.BooleanField(
        label='html_email_updates',
        required=False,
    )
    email_notify_user_talk_edits = _dj_forms.BooleanField(
        label='email_notify_user_talk_edits',
        required=False,
    )
    web_notify_followed_pages_edits = _dj_forms.BooleanField(
        label='web_notify_followed_pages_edits',
        required=False,
    )
    email_notify_followed_pages_edits = _dj_forms.BooleanField(
        label='email_notify_followed_pages_edits',
        required=False,
    )
    web_notify_talk_mentions = _dj_forms.BooleanField(
        label='web_notify_talk_mentions',
        required=False,
    )
    email_notify_talk_mentions = _dj_forms.BooleanField(
        label='email_notify_talk_mentions',
        required=False,
    )
    web_notify_message_answers = _dj_forms.BooleanField(
        label='web_notify_message_answers',
        required=False,
    )
    email_notify_message_answers = _dj_forms.BooleanField(
        label='email_notify_message_answers',
        required=False,
    )
    web_notify_topic_answers = _dj_forms.BooleanField(
        label='web_notify_topic_answers',
        required=False,
    )
    email_notify_topic_answers = _dj_forms.BooleanField(
        label='email_notify_topic_answers',
        required=False,
    )
    web_notify_thanks = _dj_forms.BooleanField(
        label='web_notify_thanks',
        required=False,
    )
    email_notify_thanks = _dj_forms.BooleanField(
        label='email_notify_thanks',
        required=False,
    )
    web_notify_failed_connection_attempts = _dj_forms.BooleanField(
        label='web_notify_failed_connection_attempts',
        required=False,
    )
    email_notify_failed_connection_attempts = _dj_forms.BooleanField(
        label='email_notify_failed_connection_attempts',
        required=False,
    )
    web_notify_permissions_edit = _dj_forms.BooleanField(
        label='web_notify_permissions_edit',
        required=False,
    )
    email_notify_permissions_edit = _dj_forms.BooleanField(
        label='email_notify_permissions_edit',
        required=False,
    )
    web_notify_user_email = _dj_forms.BooleanField(
        label='web_notify_user_email',
        required=False,
    )
    web_notify_cancelled_edits = _dj_forms.BooleanField(
        label='web_notify_cancelled_edits',
        required=False,
    )
    email_notify_cancelled_edits = _dj_forms.BooleanField(
        label='email_notify_cancelled_edits',
        required=False,
    )
    web_notify_edit_count_milestones = _dj_forms.BooleanField(
        label='web_notify_edit_count_milestones',
        required=False,
    )
    user_notification_blacklist = _dj_forms.CharField(
        label='user_notification_blacklist',
        widget=_dj_forms.Textarea(attrs={'rows': 2}),
        required=False,
    )
    page_notification_blacklist = _dj_forms.CharField(
        label='page_notification_blacklist',
        widget=_dj_forms.Textarea(attrs={'rows': 2}),
        required=False,
    )

    def __init__(self, post=None, user: _models.User = None):
        if user:
            initial = {
                'gender': user.gender.label,
                'prefered_language': user.prefered_language.code,
                'email': user.email,
                'users_can_send_emails': user.users_can_send_emails,
                'new_users_can_send_emails': user.new_users_can_send_emails,
                'send_copy_of_sent_emails': user.send_copy_of_sent_emails,
                'email_user_blacklist': '\n'.join(user.email_user_blacklist),
                'dark_mode': user.uses_dark_mode,
                'prefered_datetime_format': user.internal_object.prefered_datetime_format.id,
                'prefered_timezone': user.internal_object.prefered_timezone,
                'max_file_preview_size': user.internal_object.max_file_preview_size,
                'thumbnails_size': user.thumbnails_size,
                'show_page_content_in_diffs': user.show_page_content_in_diffs,
                'show_diff_after_revert': user.show_diff_after_revert,
                'show_hidden_categories': user.show_hidden_categories,
                'ask_revert_confirmation': user.ask_revert_confirmation,
                'mark_all_wiki_edits_as_minor': user.mark_all_wiki_edits_as_minor,
                'warn_when_no_wiki_edit_comment': user.warn_when_no_wiki_edit_comment,
                'warn_when_wiki_edit_not_published': user.warn_when_wiki_edit_not_published,
                'show_preview_above_edit_form': user.show_preview_above_edit_form,
                'show_preview_without_reload': user.show_preview_without_reload,
                'default_days_nb_in_wiki_edit_lists': user.default_days_nb_in_wiki_edit_lists,
                'default_edits_nb_in_wiki_edit_lists': user.default_edits_nb_in_wiki_edit_lists,
                'group_edits_per_page': user.group_edits_per_page,
                'mask_wiki_minor_edits': user.mask_wiki_minor_edits,
                'mask_wiki_bot_edits': user.mask_wiki_bot_edits,
                'mask_wiki_own_edits': user.mask_wiki_own_edits,
                'mask_wiki_anonymous_edits': user.mask_wiki_anonymous_edits,
                'mask_wiki_authenticated_edits': user.mask_wiki_authenticated_edits,
                'mask_wiki_categorization_edits': user.mask_wiki_categorization_edits,
                'mask_wiki_patrolled_edits': user.mask_wiki_patrolled_edits,
                'add_created_pages_to_follow_list': user.add_created_pages_to_follow_list,
                'add_modified_pages_to_follow_list': user.add_modified_pages_to_follow_list,
                'add_renamed_pages_to_follow_list': user.add_renamed_pages_to_follow_list,
                'add_deleted_pages_to_follow_list': user.add_deleted_pages_to_follow_list,
                'add_reverted_pages_to_follow_list': user.add_reverted_pages_to_follow_list,
                'add_created_topics_to_follow_list': user.add_created_topics_to_follow_list,
                'add_replied_to_topics_to_follow_list': user.add_replied_to_topics_to_follow_list,
                'search_default_results_nb': user.search_default_results_nb,
                'search_mode': user.search_mode.value,
                'email_update_notification_frequency': user.email_update_notification_frequency.value,
                'html_email_updates': user.html_email_updates,
                'email_notify_user_talk_edits': user.email_notify_user_talk_edits,
                'web_notify_followed_pages_edits': user.web_notify_followed_pages_edits,
                'email_notify_followed_pages_edits': user.email_notify_followed_pages_edits,
                'web_notify_talk_mentions': user.web_notify_talk_mentions,
                'email_notify_talk_mentions': user.email_notify_talk_mentions,
                'web_notify_message_answers': user.web_notify_message_answers,
                'email_notify_message_answers': user.email_notify_message_answers,
                'web_notify_topic_answers': user.web_notify_topic_answers,
                'email_notify_topic_answers': user.email_notify_topic_answers,
                'web_notify_thanks': user.web_notify_thanks,
                'email_notify_thanks': user.email_notify_thanks,
                'web_notify_failed_connection_attempts': user.web_notify_failed_connection_attempts,
                'email_notify_failed_connection_attempts': user.email_notify_failed_connection_attempts,
                'web_notify_permissions_edit': user.notif_permissions_edit_web,
                'email_notify_permissions_edit': user.notif_permissions_edit_email,
                'web_notify_user_email': user.notif_user_email_web,
                'web_notify_cancelled_edits': user.web_notify_cancelled_edits,
                'email_notify_cancelled_edits': user.email_notify_cancelled_edits,
                'web_notify_edit_count_milestones': user.web_notify_edit_count_milestones,
                'user_notification_blacklist': '\n'.join(user.user_notification_blacklist),
                'page_notification_blacklist': '\n'.join(user.page_notification_blacklist),
            }
        else:
            initial = {}

        super().__init__('user_settings', True, post=post, initial=initial)

        self.fields['prefered_language'].choices = tuple(
            (language.code, language.name)
            for language in _models.Language.objects.order_by('name')
        )
        now = _utils.now()
        self.fields['prefered_datetime_format'].choices = tuple(
            (dtf.id, user.prefered_language.format_datetime(now, dtf.format))
            for dtf in _models.DateTimeFormat.objects.all()
        )


class UserSettingsPageContext(_user_page_context.UserPageContext):
    """Context class for user settings pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            target_user: _models.User,
            form: UserSettingsForm,
    ):
        """Create a page context for a user’s settings page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param target_user: User of the requested page.
        :param form: Settings form.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            target_user=target_user,
        )
        self._form = form

    @property
    def form(self) -> UserSettingsForm:
        return self._form
