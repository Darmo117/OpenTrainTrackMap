"""This module defines the website’s database models."""
from __future__ import annotations

import datetime as _dt
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.core.exceptions as _dj_exc
import django.db.models as _dj_models
import pytz as _pytz
from django.conf import settings as _dj_settings

from . import _i18n_models as _i18n_m
from .. import model_fields, settings as _settings
from ..api import data_types as _data_types, groups as _groups, permissions as _perms, \
    timezones as _tz, utils as _utils
from ..api.wiki import constants as _w_cons, namespaces as _w_ns, notifications as _notif, search_engine as _se


def user_group_label_validator(value: str):
    if not value.isascii() or not value.isalnum():
        raise _dj_exc.ValidationError('invalid user group label', code='user_group_invalid_label')


class UserGroup(_dj_models.Model):
    """User groups define permissions to grant to user that belong to them."""
    label = _dj_models.CharField(max_length=20, unique=True, validators=[user_group_label_validator])
    assignable_by_users = _dj_models.BooleanField(default=True)
    permissions = model_fields.CommaSeparatedStringsField()

    class Meta:
        ordering = ('assignable_by_users', 'label')

    @classmethod
    def get_assignable_groups(cls) -> _dj_models.QuerySet[UserGroup]:
        """Return a query set of all user groups that are assignable by users."""
        return cls.objects.filter(assignable_by_users=True)

    def has_permission(self, perm: str) -> bool:
        """Check whether this group has the given permission.

        :param perm: The permission.
        :return: True if this group contains the permission, false otherwise.
        """
        return perm in self.permissions

    def delete(self, using=None, keep_parents=False):
        if not self.assignable_by_users:
            raise RuntimeError(f'cannot delete "{self.label}" group')
        super().delete(using=using, keep_parents=keep_parents)


def username_validator(value: str):
    """Validate a username. Usernames must be valid page titles and not contain any '/'.

    :param value: The username.
    """
    if '/' in value or _settings.INVALID_TITLE_REGEX.search(value):
        raise _dj_exc.ValidationError('invalid username', code='invalid')


class User:
    """Wrapper class around CustomUser and AnonymousUser classes."""

    def __init__(self, dj_user: CustomUser):
        """Create a wrapper around the given user.

        :param dj_user: Either a CustomUser or AnonymousUser.
        """
        self._user = dj_user

    @property
    def exists(self) -> bool:
        """Whether this user exists in the database.
        Is true only for users that are not authenticated and no edits were ever made with their IP."""
        return self._user.pk is not None

    @property
    def internal_object(self) -> CustomUser:
        """Reference to the internal database user object."""
        return self._user

    @property
    def is_authenticated(self) -> bool:
        """Whether this user is authenticated."""
        # Not using is_authenticated as it is True even for anonymous users
        return self._user.ip is None

    @property
    def is_bot(self):
        """Whether this user is a bot account."""
        return self._user.is_bot

    @property
    def is_new(self):
        """Whether this user is new (anonymous or less than 30 days)."""
        return not self.exists or (self._user.date_joined - _utils.now()).days <= 30

    @property
    def ip(self) -> str | None:
        """This user’s IP. May be None if the user is authenticated."""
        return self._user.ip

    @property
    def username(self) -> str:
        """This user’s username."""
        return self._user.username

    @username.setter
    def username(self, value: str):
        """Set this user’s username. User must not be anonymous."""
        self._check_authenticated()
        self._user.username = value

    @property
    def hide_username(self) -> bool:
        """Whether this user’s username has to be hidden in pages."""
        return self._user.hide_username

    @hide_username.setter
    def hide_username(self, value: bool):
        """Set whether this user’s username has to be hidden in pages. User must not be anonymous."""
        self._check_authenticated()
        self._user.hide_username = value

    @property
    def password(self) -> str:
        """This user’s password."""
        return self._user.password

    @password.setter
    def password(self, value: str):
        """Set this user’s password. User must not be anonymous.
        Calls the ``set_password()`` method on the internal object.
        """
        self._check_authenticated()
        self._user.set_password(value)

    @property
    def email(self) -> str:
        """This user’s email address."""
        return self._user.email

    @email.setter
    def email(self, value: str):
        """Set this user’s email address. User must not be anonymous."""
        self._check_authenticated()
        self._user.email = value

    @property
    def preferred_language(self) -> _settings.UILanguage:
        """This user’s preferred language."""
        if not self.exists:
            return _settings.LANGUAGES[_settings.DEFAULT_LANGUAGE_CODE]
        return _settings.LANGUAGES[self._user.preferred_language.code]

    @preferred_language.setter
    def preferred_language(self, value: _settings.UILanguage):
        """Set this user’s preferred language. User must not be anonymous."""
        self._check_authenticated()
        try:
            self._user.preferred_language = _i18n_m.Language.objects.get(code=value.code)
        except _i18n_m.Language.DoesNotExist:  # Should never happen
            raise ValueError(f'invalid language code {value.code}')

    @property
    def preferred_timezone(self) -> _pytz.BaseTzInfo:
        """This user’s preferred timezone."""
        if self.exists:
            return _pytz.timezone(self._user.preferred_timezone)
        else:
            return _pytz.timezone(_dj_settings.TIME_ZONE)

    @preferred_timezone.setter
    def preferred_timezone(self, value: _pytz.BaseTzInfo):
        """Set this user’s preferred timezone. User must not be anonymous."""
        self._check_authenticated()
        self._user.preferred_timezone = value.zone

    @property
    def preferred_datetime_format(self) -> str:
        """This user’s preferred datetime format."""
        if self.exists:
            return self._user.preferred_datetime_format.format
        else:
            return self.preferred_language.default_datetime_format

    @preferred_datetime_format.setter
    def preferred_datetime_format(self, value: int):
        """Set this user’s preferred datetime format to the one with the given ID. User must not be anonymous."""
        self._check_authenticated()
        try:
            self._user.preferred_datetime_format = _i18n_m.DateTimeFormat.objects.get(id=value)
        except _i18n_m.DateTimeFormat.DoesNotExist:
            raise ValueError(f'invalid datetime format ID: {value}')

    @property
    def gender(self) -> _data_types.UserGender:
        """This user’s gender."""
        return _data_types.GENDERS[self._user.gender_code]

    @gender.setter
    def gender(self, value: _data_types.UserGender):
        """Set this user’s gender. User must not be anonymous."""
        self._check_authenticated()
        self._user.gender_code = value.label

    @property
    def uses_dark_mode(self) -> bool:
        """Whether this user uses dark mode."""
        return self._user.uses_dark_mode

    @uses_dark_mode.setter
    def uses_dark_mode(self, value: bool):
        """Set whether this user uses dark mode. User must not be anonymous."""
        self._check_authenticated()
        self._user.uses_dark_mode = value

    @property
    def users_can_send_emails(self) -> bool:
        """Whether users can send emails to this user."""
        return self._user.users_can_send_emails

    @users_can_send_emails.setter
    def users_can_send_emails(self, value: bool):
        """Set whether users can send emails to this user."""
        self._check_authenticated()
        self._user.users_can_send_emails = value

    @property
    def new_users_can_send_emails(self) -> bool:
        """Whether new users can send emails to this user."""
        return self._user.new_users_can_send_emails

    @new_users_can_send_emails.setter
    def new_users_can_send_emails(self, value: bool):
        """Set whether new users can send emails to this user."""
        self._check_authenticated()
        self._user.new_users_can_send_emails = value

    @property
    def send_copy_of_sent_emails(self) -> bool:
        """Whether to send copies of emails this user sends."""
        return self._user.send_copy_of_sent_emails

    @send_copy_of_sent_emails.setter
    def send_copy_of_sent_emails(self, value: bool):
        """Set whether to send copies of emails this user sends."""
        self._check_authenticated()
        self._user.send_copy_of_sent_emails = value

    @property
    def email_user_blacklist(self) -> list[str]:
        """List of users that cannot send emails to this user."""
        # noinspection PyTypeChecker
        return list(self._user.email_user_blacklist or [])

    @email_user_blacklist.setter
    def email_user_blacklist(self, value: _typ.Iterable[str]):
        """Set the list of users that cannot send emails to this user."""
        self._check_authenticated()
        self._user.email_user_blacklist = value

    @property
    def max_file_preview_size(self) -> tuple[int, int]:
        """Tuple corresponding to the maximum size of the wiki file previews."""
        n1, n2 = self._user.max_file_preview_size.split(',')
        return int(n1), int(n2)

    @max_file_preview_size.setter
    def max_file_preview_size(self, value: tuple[int, int]):
        """Set the maximum size of the wiki file previews."""
        self._check_authenticated()
        self._user.max_file_preview_size = f'{value[0]},{value[1]}'

    @property
    def thumbnails_size(self) -> int:
        """Maximum width and height of media thumbnails in wiki pages."""
        return self._user.thumbnails_size

    @thumbnails_size.setter
    def thumbnails_size(self, value: int):
        """Set the maximum width and height of media thumbnails in wiki pages."""
        self._check_authenticated()
        self._user.thumbnails_size = value

    @property
    def show_page_content_in_diffs(self) -> bool:
        """Whether to show the content of pages in diffs."""
        return self._user.show_page_content_in_diffs

    @show_page_content_in_diffs.setter
    def show_page_content_in_diffs(self, value: bool):
        """Set whether to show the content of pages in diffs."""
        self._check_authenticated()
        self._user.show_page_content_in_diffs = value

    @property
    def show_diff_after_revert(self) -> bool:
        """Whether to show the diff after a revert."""
        return self._user.show_diff_after_revert

    @show_diff_after_revert.setter
    def show_diff_after_revert(self, value: bool):
        """Set whether to show the diff after a revert."""
        self._check_authenticated()
        self._user.show_diff_after_revert = value

    @property
    def show_hidden_categories(self) -> bool:
        """Whether to show hidden categories."""
        return self._user.show_hidden_categories

    @show_hidden_categories.setter
    def show_hidden_categories(self, value: bool):
        """Set whether to show hidden categories."""
        self._check_authenticated()
        self._user.show_hidden_categories = value

    @property
    def ask_revert_confirmation(self) -> bool:
        """Whether to ask confirmation before reverting a wiki edit."""
        return self._user.ask_revert_confirmation

    @ask_revert_confirmation.setter
    def ask_revert_confirmation(self, value: bool):
        """Set whether to ask confirmation before reverting a wiki edit."""
        self._check_authenticated()
        self._user.ask_revert_confirmation = value

    @property
    def uses_editor_syntax_highlighting(self) -> bool:
        """Whether this user uses the syntax highlighting wiki editor."""
        return self._user.uses_editor_syntax_highlighting

    @uses_editor_syntax_highlighting.setter
    def uses_editor_syntax_highlighting(self, value: bool):
        """Set whether this user uses the syntax highlighting wiki editor."""
        self._check_authenticated()
        self._user.uses_editor_syntax_highlighting = value

    @property
    def mark_all_wiki_edits_as_minor(self) -> bool:
        """Whether to mark all wiki edits as minor."""
        return self._user.mark_all_wiki_edits_as_minor

    @mark_all_wiki_edits_as_minor.setter
    def mark_all_wiki_edits_as_minor(self, value: bool):
        """Set whether to mark all wiki edits as minor."""
        self._check_authenticated()
        self._user.mark_all_wiki_edits_as_minor = value

    @property
    def warn_when_no_wiki_edit_comment(self) -> bool:
        """Whether to warn when a wiki edit is published without a summary."""
        return self._user.warn_when_no_wiki_edit_comment

    @warn_when_no_wiki_edit_comment.setter
    def warn_when_no_wiki_edit_comment(self, value: bool):
        """Set whether to warn when a wiki edit is published without a summary."""
        self._check_authenticated()
        self._user.warn_when_no_wiki_edit_comment = value

    @property
    def warn_when_wiki_edit_not_published(self) -> bool:
        """Whether to warn when this user quits the wiki edit form with unpublished changes."""
        return self._user.warn_when_wiki_edit_not_published

    @warn_when_wiki_edit_not_published.setter
    def warn_when_wiki_edit_not_published(self, value: bool):
        """Set whether to warn when this user quits the wiki edit form with unpublished changes."""
        self._check_authenticated()
        self._user.warn_when_wiki_edit_not_published = value

    @property
    def show_preview_above_edit_form(self) -> bool:
        """Whether to show previews above the edit form."""
        return self._user.show_preview_above_edit_form

    @show_preview_above_edit_form.setter
    def show_preview_above_edit_form(self, value: bool):
        """Set whether to show previews above the edit form."""
        self._check_authenticated()
        self._user.show_preview_above_edit_form = value

    @property
    def show_preview_without_reload(self) -> bool:
        """Whether to show the preview without reloading the page."""
        return self._user.show_preview_without_reload

    @show_preview_without_reload.setter
    def show_preview_without_reload(self, value: bool):
        """Set whether to show the preview without reloading the page."""
        self._check_authenticated()
        self._user.show_preview_without_reload = value

    @property
    def default_days_nb_in_wiki_edit_lists(self) -> int:
        """Default number of days to show in the wiki RC and FL."""
        return self._user.days_nb_rc_fl_logs

    @default_days_nb_in_wiki_edit_lists.setter
    def default_days_nb_in_wiki_edit_lists(self, value: int):
        """Set the default number of days to show in the wiki RC and FL."""
        self._check_authenticated()
        self._user.days_nb_rc_fl_logs = value

    @property
    def default_edits_nb_in_wiki_edit_lists(self) -> int:
        """Default number of edits to show in the wiki RC, logs and FL."""
        return self._user.edits_nb_rc_fl_logs

    @default_edits_nb_in_wiki_edit_lists.setter
    def default_edits_nb_in_wiki_edit_lists(self, value: int):
        """Set the default number of edits to show in the wiki RC, logs and FL."""
        self._check_authenticated()
        self._user.edits_nb_rc_fl_logs = value

    @property
    def group_edits_per_page(self) -> bool:
        """Whether to group edits per page in RC and FL."""
        return self._user.group_edits_per_page_rc_fl

    @group_edits_per_page.setter
    def group_edits_per_page(self, value: bool):
        """Set whether to group edits per page in RC and FL."""
        self._check_authenticated()
        self._user.group_edits_per_page_rc_fl = value

    @property
    def mask_wiki_minor_edits(self) -> bool:
        """Whether to mask minor edits in RC and FL."""
        return self._user.mask_wiki_minor_edits

    @mask_wiki_minor_edits.setter
    def mask_wiki_minor_edits(self, value: bool):
        """Set whether to mask minor edits in RC and FL."""
        self._check_authenticated()
        self._user.mask_wiki_minor_edits = value

    @property
    def mask_wiki_bot_edits(self) -> bool:
        """Whether to mask bot edits in RC and FL."""
        return self._user.mask_wiki_bot_edits

    @mask_wiki_bot_edits.setter
    def mask_wiki_bot_edits(self, value: bool):
        """Set whether to mask bot edits in RC and FL."""
        self._check_authenticated()
        self._user.mask_wiki_bot_edits = value

    @property
    def mask_wiki_own_edits(self) -> bool:
        """Whether to mask this user’s edits in RC and FL."""
        return self._user.mask_wiki_own_edits

    @mask_wiki_own_edits.setter
    def mask_wiki_own_edits(self, value: bool):
        """Set whether to mask this user’s edits in RC and FL."""
        self._check_authenticated()
        self._user.mask_wiki_own_edits = value

    @property
    def mask_wiki_anonymous_edits(self) -> bool:
        """Whether to mask anonymous edits in RC and FL."""
        return self._user.mask_wiki_anonymous_edits

    @mask_wiki_anonymous_edits.setter
    def mask_wiki_anonymous_edits(self, value: bool):
        """Set whether to mask anonymous edits in RC and FL."""
        self._check_authenticated()
        self._user.mask_wiki_anonymous_edits = value

    @property
    def mask_wiki_authenticated_edits(self) -> bool:
        """Whether to mask authenticated edits in RC and FL."""
        return self._user.mask_wiki_authenticated_edits

    @mask_wiki_authenticated_edits.setter
    def mask_wiki_authenticated_edits(self, value: bool):
        """Set whether to mask authenticated edits in RC and FL."""
        self._check_authenticated()
        self._user.mask_wiki_authenticated_edits = value

    @property
    def mask_wiki_categorization_edits(self) -> bool:
        """Whether to mask page categorization edits in RC and FL."""
        return self._user.mask_wiki_categorization_edits

    @mask_wiki_categorization_edits.setter
    def mask_wiki_categorization_edits(self, value: bool):
        """Set whether to mask page categorization edits in RC and FL."""
        self._check_authenticated()
        self._user.mask_wiki_categorization_edits = value

    @property
    def mask_wiki_patrolled_edits(self) -> bool:
        """Whether to mask patrolled edits in RC and FL."""
        return self._user.mask_wiki_patrolled_edits

    @mask_wiki_patrolled_edits.setter
    def mask_wiki_patrolled_edits(self, value: bool):
        """Set whether to mask patrolled edits in RC and FL."""
        self._check_authenticated()
        self._user.mask_wiki_patrolled_edits = value

    @property
    def add_created_pages_to_follow_list(self) -> bool:
        """Whether to add created pages to this user’s FL."""
        return self._user.fl_add_created_pages

    @add_created_pages_to_follow_list.setter
    def add_created_pages_to_follow_list(self, value: bool):
        """Set whether to add created pages to this user’s FL."""
        self._check_authenticated()
        self._user.fl_add_created_pages = value

    @property
    def add_modified_pages_to_follow_list(self) -> bool:
        """Whether to add modified pages to this user’s FL."""
        return self._user.fl_add_modified_pages

    @add_modified_pages_to_follow_list.setter
    def add_modified_pages_to_follow_list(self, value: bool):
        """Set whether to add modified pages to this user’s FL."""
        self._check_authenticated()
        self._user.fl_add_modified_pages = value

    @property
    def add_renamed_pages_to_follow_list(self) -> bool:
        """Whether to add renamed pages to this user’s FL."""
        return self._user.fl_add_renamed_pages

    @add_renamed_pages_to_follow_list.setter
    def add_renamed_pages_to_follow_list(self, value: bool):
        """Set whether to add renamed pages to this user’s FL."""
        self._check_authenticated()
        self._user.fl_add_renamed_pages = value

    @property
    def add_deleted_pages_to_follow_list(self) -> bool:
        """Whether to add deleted pages to this user’s FL."""
        return self._user.fl_add_deleted_pages

    @add_deleted_pages_to_follow_list.setter
    def add_deleted_pages_to_follow_list(self, value: bool):
        """Set whether to add deleted pages to this user’s FL."""
        self._check_authenticated()
        self._user.fl_add_deleted_pages = value

    @property
    def add_reverted_pages_to_follow_list(self) -> bool:
        """Whether to add reverted pages to this user’s FL."""
        return self._user.fl_add_reverted_pages

    @add_reverted_pages_to_follow_list.setter
    def add_reverted_pages_to_follow_list(self, value: bool):
        """Set whether to add reverted pages to this user’s FL."""
        self._check_authenticated()
        self._user.fl_add_reverted_pages = value

    @property
    def add_created_topics_to_follow_list(self) -> bool:
        """Whether to add created topics to this user’s FL."""
        return self._user.fl_add_created_topics

    @add_created_topics_to_follow_list.setter
    def add_created_topics_to_follow_list(self, value: bool):
        """Set whether to add created topics to this user’s FL."""
        self._check_authenticated()
        self._user.fl_add_created_topics = value

    @property
    def add_replied_to_topics_to_follow_list(self) -> bool:
        """Whether to add replied to topics to this user’s FL."""
        return self._user.fl_add_replied_to_topics

    @add_replied_to_topics_to_follow_list.setter
    def add_replied_to_topics_to_follow_list(self, value: bool):
        """Set whether to add replied to topics to this user’s FL."""
        self._check_authenticated()
        self._user.fl_add_replied_to_topics = value

    @property
    def search_default_results_nb(self) -> int:
        """Default number of search results per page."""
        return self._user.search_default_results_nb

    @search_default_results_nb.setter
    def search_default_results_nb(self, value: int):
        """Set the default number of search results per page."""
        self._check_authenticated()
        self._user.search_default_results_nb = value

    @property
    def search_mode(self) -> _se.SearchMode:
        """Search engine mode."""
        return _se.SearchMode(self._user.search_mode)

    @search_mode.setter
    def search_mode(self, value: _se.SearchMode):
        """Set the search engine mode."""
        self._check_authenticated()
        self._user.search_mode = value.value

    @property
    def email_update_notification_frequency(self) -> _notif.NotificationEmailFrequency:
        """Frequency of notification emails."""
        if self.exists:
            return _notif.NotificationEmailFrequency(self._user.notif_email_frequency)
        else:
            return _notif.NotificationEmailFrequency.NONE

    @email_update_notification_frequency.setter
    def email_update_notification_frequency(self, value: _notif.NotificationEmailFrequency):
        """Set the frequency of notification emails."""
        self._check_authenticated()
        self._user.notif_email_frequency = value.value

    @property
    def html_email_updates(self) -> bool:
        """Whether to send emails as HTML."""
        return self._user.html_email_updates

    @html_email_updates.setter
    def html_email_updates(self, value: bool):
        """Set whether to send emails as HTML."""
        self._check_authenticated()
        self._user.html_email_updates = value

    @property
    def email_notify_user_talk_edits(self) -> bool:
        """Whether to send email notifications when this user’s talk page is updated."""
        return self._user.notif_user_talk_edits_email

    @email_notify_user_talk_edits.setter
    def email_notify_user_talk_edits(self, value: bool):
        """Set whether to send email notifications when this user’s talk page is updated."""
        self._check_authenticated()
        self._user.notif_user_talk_edits_email = value

    @property
    def web_notify_followed_pages_edits(self) -> bool:
        """Whether to send web notifications when this user’s followed pages are edited."""
        return self._user.notif_followed_pages_edits_web

    @web_notify_followed_pages_edits.setter
    def web_notify_followed_pages_edits(self, value: bool):
        """Set whether to send web notifications when this user’s followed pages are edited."""
        self._check_authenticated()
        self._user.notif_followed_pages_edits_web = value

    @property
    def email_notify_followed_pages_edits(self) -> bool:
        """Whether to send email notifications when this user’s followed pages are edited."""
        return self._user.notif_followed_pages_edits_email

    @email_notify_followed_pages_edits.setter
    def email_notify_followed_pages_edits(self, value: bool):
        """Set whether to send email notifications when this user’s followed pages are edited."""
        self._check_authenticated()
        self._user.notif_followed_pages_edits_email = value

    @property
    def web_notify_talk_mentions(self) -> bool:
        """Whether to send web notifications when this user is mentioned."""
        return self._user.notif_talk_mentions_web

    @web_notify_talk_mentions.setter
    def web_notify_talk_mentions(self, value: bool):
        """Set whether to send web notifications when this user is mentioned."""
        self._check_authenticated()
        self._user.notif_talk_mentions_web = value

    @property
    def email_notify_talk_mentions(self) -> bool:
        """Whether to send email notifications when this user is mentioned."""
        return self._user.notif_talk_mentions_email

    @email_notify_talk_mentions.setter
    def email_notify_talk_mentions(self, value: bool):
        """Set whether to send email notifications when this user is mentioned."""
        self._check_authenticated()
        self._user.notif_talk_mentions_email = value

    @property
    def web_notify_message_answers(self) -> bool:
        """Whether to send web notifications when a message of this user receives a response."""
        return self._user.notif_message_answers_web

    @web_notify_message_answers.setter
    def web_notify_message_answers(self, value: bool):
        """Set whether to send web notifications when a message of this user receives a response."""
        self._check_authenticated()
        self._user.notif_message_answers_web = value

    @property
    def email_notify_message_answers(self) -> bool:
        """Whether to send email notifications when a message of this user receives a response."""
        return self._user.notif_message_answers_email

    @email_notify_message_answers.setter
    def email_notify_message_answers(self, value: bool):
        """Set whether to send email notifications when a message of this user receives a response."""
        self._check_authenticated()
        self._user.notif_message_answers_email = value

    @property
    def web_notify_topic_answers(self) -> bool:
        """Whether to send web notifications when a topic created by this user receives a response."""
        return self._user.notif_topic_answers_web

    @web_notify_topic_answers.setter
    def web_notify_topic_answers(self, value: bool):
        """Set whether to send web notifications when a topic created by this user receives a response."""
        self._check_authenticated()
        self._user.notif_topic_answers_web = value

    @property
    def email_notify_topic_answers(self) -> bool:
        """Whether to send email notifications when a topic created by this user receives a response."""
        return self._user.notif_topic_answers_email

    @email_notify_topic_answers.setter
    def email_notify_topic_answers(self, value: bool):
        """Set whether to send email notifications when a topic created by this user receives a response."""
        self._check_authenticated()
        self._user.notif_topic_answers_email = value

    @property
    def web_notify_thanks(self) -> bool:
        """Whether to send web notifications when someone thanks this user."""
        return self._user.notif_thanks_web

    @web_notify_thanks.setter
    def web_notify_thanks(self, value: bool):
        """Set whether to send web notifications when someone thanks this user."""
        self._check_authenticated()
        self._user.notif_thanks_web = value

    @property
    def email_notify_thanks(self) -> bool:
        """Whether to send email notifications when someone thanks this user."""
        return self._user.notif_thanks_email

    @email_notify_thanks.setter
    def email_notify_thanks(self, value: bool):
        """Set whether to send email notifications when someone thanks this user."""
        self._check_authenticated()
        self._user.notif_thanks_email = value

    @property
    def web_notify_failed_connection_attempts(self) -> bool:
        """Whether to send web notifications when there was a failed connection attempt to this user’s account."""
        return self._user.notif_failed_connection_attempts_web

    @web_notify_failed_connection_attempts.setter
    def web_notify_failed_connection_attempts(self, value: bool):
        """Set whether to send web notifications when there was a failed connection attempt to this user’s account."""
        self._check_authenticated()
        self._user.notif_failed_connection_attempts_web = value

    @property
    def email_notify_failed_connection_attempts(self) -> bool:
        """Whether to send email notifications when there was a failed connection attempt to this user’s account."""
        return self._user.notif_failed_connection_attempts_email

    @email_notify_failed_connection_attempts.setter
    def email_notify_failed_connection_attempts(self, value: bool):
        """Set whether to send email notifications when there was a failed connection attempt to this user’s account."""
        self._check_authenticated()
        self._user.notif_failed_connection_attempts_email = value

    @property
    def web_notify_permissions_edit(self) -> bool:
        """Whether to send web notifications when this user’s permissions are edited."""
        return self._user.notif_permissions_edit_web

    @web_notify_permissions_edit.setter
    def web_notify_permissions_edit(self, value: bool):
        """Set whether to send web notifications when this user’s permissions are edited."""
        self._check_authenticated()
        self._user.notif_permissions_edit_web = value

    @property
    def email_notify_permissions_edit(self) -> bool:
        """Whether to send email notifications when this user’s permissions are edited."""
        return self._user.notif_permissions_edit_email

    @email_notify_permissions_edit.setter
    def email_notify_permissions_edit(self, value: bool):
        """Set whether to send email notifications when this user’s permissions are edited."""
        self._check_authenticated()
        self._user.notif_permissions_edit_email = value

    @property
    def web_notify_user_email_web(self) -> bool:
        """Whether to send web notifications when this user receives an email from another user."""
        return self._user.notif_user_email_web

    @web_notify_user_email_web.setter
    def web_notify_user_email_web(self, value: bool):
        """Set whether to send web notifications when this user receives an email from another user."""
        self._check_authenticated()
        self._user.notif_user_email_web = value

    @property
    def web_notify_cancelled_edits(self) -> bool:
        """Whether to send web notifications when one of this user’s edits is cancelled."""
        return self._user.notif_cancelled_edits_web

    @web_notify_cancelled_edits.setter
    def web_notify_cancelled_edits(self, value: bool):
        """Set whether to send web notifications when one of this user’s edits is cancelled."""
        self._check_authenticated()
        self._user.notif_cancelled_edits_web = value

    @property
    def email_notify_cancelled_edits(self) -> bool:
        """Whether to send email notifications when one of this user’s edits is cancelled."""
        return self._user.notif_cancelled_edits_email

    @email_notify_cancelled_edits.setter
    def email_notify_cancelled_edits(self, value: bool):
        """Set whether to send email notifications when one of this user’s edits is cancelled."""
        self._check_authenticated()
        self._user.notif_cancelled_edits_email = value

    @property
    def web_notify_edit_count_milestones(self) -> bool:
        """Whether to send web notifications when this user reaches an edit count milestone."""
        return self._user.notif_edit_count_milestones_web

    @web_notify_edit_count_milestones.setter
    def web_notify_edit_count_milestones(self, value: bool):
        """Set whether to send web notifications when this user reaches an edit count milestone."""
        self._check_authenticated()
        self._user.notif_edit_count_milestones_web = value

    @property
    def user_notification_blacklist(self) -> list[str]:
        """List of users whose notifications should be ignored."""
        # noinspection PyTypeChecker
        return list(self._user.user_notification_blacklist or [])

    @user_notification_blacklist.setter
    def user_notification_blacklist(self, value: _typ.Iterable[str]):
        """Set the list of users whose notifications should be ignored."""
        self._check_authenticated()
        self._user.user_notification_blacklist = value

    @property
    def page_notification_blacklist(self) -> list[str]:
        """List of pages whose notifications should be ignored."""
        # noinspection PyTypeChecker
        return list(self._user.page_notification_blacklist or [])

    @page_notification_blacklist.setter
    def page_notification_blacklist(self, value: _typ.Iterable[str]):
        """Set the list of pages whose notifications should be ignored."""
        self._check_authenticated()
        self._user.page_notification_blacklist = value

    @property
    def block(self) -> UserBlock | None:
        """This user’s block status or None if the user’s not blocked."""
        if not self.exists:
            return None
        try:
            return self._user.block
        except _dj_exc.ObjectDoesNotExist:
            return None

    @property
    def is_blocked(self):
        """Whether this user is blocked."""
        return (b := self.block) and b.is_active

    @property
    def edits(self) -> _dj_models.Manager[object]:
        """A Manager object for this user’s edit groups."""
        # return self._user.edit_groups if self.exists else _dj_auth_models.EmptyManager(_ottm_m.EditGroup)
        return None

    @property
    def wiki_edits(self) -> _dj_models.QuerySet[PageRevision]:
        """A QuerySet object for the wiki page edits made by this user."""
        if self.exists:
            return PageRevision.objects.filter(author=self._user)
        else:
            return _dj_auth_models.EmptyManager(Message).all()

    @property
    def wiki_topics(self) -> _dj_models.Manager[Topic]:
        """A Manager object for the wiki topics created by this user."""
        return self._user.wiki_topics

    @property
    def wiki_messages(self) -> _dj_models.Manager[Message]:
        """A Manager object for the wiki messages posted by this user."""
        return self._user.wiki_messages if self.exists else _dj_auth_models.EmptyManager(Message)

    def can_send_emails_to(self, other: User) -> bool:
        """Check whether this user can send emails to the given one.

        :param other: A user.
        :return: True if this user can send emails to the specified one, false otherwise.
        """
        return (other.can_receive_emails and self.is_authenticated and not self.is_blocked and other.email
                and (not self.is_new or other.new_users_can_send_emails)
                and self.username not in other.email_user_blacklist)

    @property
    def can_receive_emails(self):
        """Whether this user can receive emails."""
        return (self.exists and not self.is_bot and self.is_authenticated
                and not self.is_blocked and self.users_can_send_emails)

    def has_permission(self, perm: str) -> bool:
        """Check whether this user has the given permission.

        :param perm: The permission.
        :return: True if the user has the permission, false otherwise.
        """
        return any(g.has_permission(perm) for g in self.get_groups())

    def is_in_group(self, group: UserGroup) -> bool:
        """Check whether this user is in the given group.

        :param group: The group.
        :return: True if the user is in the group, false otherwise.
        """
        return self.get_groups().filter(id=group.id).exists()

    def get_groups(self) -> _dj_models.QuerySet[UserGroup]:
        """Return a query set of this user’s groups."""
        if not self.exists:
            return UserGroup.objects.filter(label=_groups.GROUP_ALL)
        return self._user.groups.all()

    def get_followed_pages(self) -> list[Page]:
        """Return the list of pages this user follows, ordered by namespace ID and title."""
        from ..api.wiki import pages
        if not self.is_authenticated:
            return []
        return [
            pages.get_page(_w_ns.NAMESPACE_IDS[pfs.page_namespace_id], pfs.page_title)
            for pfs in self.internal_object.followed_pages.order_by('page_namespace_id', 'page_title')
        ]

    def notes_count(self) -> int:
        """Return the total number of notes created by this user."""
        if not self.exists:
            return 0
        # return (_ottm_m.ObjectAdded.objects
        #         .filter(edit_group__author=self._user, object_type=_ottm_m.Note.__name__)
        #         .count())
        return 0

    def edits_count(self) -> int:
        """Return the total number of edits on objects and relations made by this user."""
        if not self.exists:
            return 0
        return 0  # FIXME
        # return (self._user.edit_groups  # Get all edit groups for this user
        #         .annotate(edits_count=dj_models.Count('edits'))  # Count number of edits for each group
        #         .aggregate(dj_models.Sum('edits_count')))  # Sum all counts

    def edit_groups_count(self) -> int:
        """Return the number of edit groups made by this user."""
        return self._user.edit_groups.count() if self.exists else 0

    def wiki_edits_count(self) -> int:
        """Return the number of edits this user made on the wiki."""
        return PageRevision.objects.filter(author=self._user).count() if self.exists else 0

    def wiki_topics_count(self) -> int:
        """Return the number of topics this user created on the wiki."""
        return self._user.wiki_topics.count() if self.exists else 0

    def wiki_messages_count(self) -> int:
        """Return the number of messages this user posted on the wiki."""
        return self._user.wiki_messages.count() if self.exists else 0

    def _check_authenticated(self):
        if not self.is_authenticated:
            raise RuntimeError('user is not authenticated')

    def __eq__(self, other: User):
        return self.internal_object == other.internal_object

    def __hash__(self):
        return hash(self.internal_object)


def thumbnail_size_validator(n: int):
    if not (100 <= n <= 600):
        raise _dj_exc.ValidationError('invalid thumbnail size', code='invalid_thumbnail_size')


def days_nb_rc_fl_logs_validator(n: int):
    if not (1 <= n <= 30):
        raise _dj_exc.ValidationError('invalid number of days', code='invalid_revisions_days_nb')


def edits_nb_rc_fl_logs_validator(n: int):
    if not (1 <= n <= 1000):
        raise _dj_exc.ValidationError('invalid number of edits', code='invalid_revisions_edits_nb')


def search_results_nb_validator(n: int):
    if not (1 <= n <= 50):
        raise _dj_exc.ValidationError('invalid number of search results', code='invalid_search_results_nb')


class CustomUser(_dj_auth_models.AbstractUser):
    """Custom user class to override the default username validator and add additional data.
    Never edit instances of this model directly, always do it through the ``User`` class.
    """
    username_validator = username_validator
    hide_username = _dj_models.BooleanField(default=False)
    # IP for anonymous accounts
    ip = _dj_models.CharField(max_length=39, null=True, blank=True)
    preferred_language = _dj_models.ForeignKey(_i18n_m.Language, on_delete=_dj_models.PROTECT)
    groups = _dj_models.ManyToManyField(UserGroup, related_name='users')
    gender_code = _dj_models.CharField(max_length=10, choices=tuple((v, v) for v in _data_types.GENDERS.keys()),
                                       default=_data_types.GENDER_N.label)
    uses_dark_mode = _dj_models.BooleanField(default=False)
    preferred_datetime_format = _dj_models.ForeignKey(_i18n_m.DateTimeFormat, on_delete=_dj_models.PROTECT)
    preferred_timezone = _dj_models.CharField(max_length=50, choices=((tz, tz) for tz in _tz.TIMEZONES),
                                              default=_pytz.UTC.zone)
    is_bot = _dj_models.BooleanField(default=False)
    # Wiki-related
    users_can_send_emails = _dj_models.BooleanField(default=True)
    new_users_can_send_emails = _dj_models.BooleanField(default=True)
    send_copy_of_sent_emails = _dj_models.BooleanField(default=False)  # TODO use
    email_user_blacklist = model_fields.CommaSeparatedStringsField(separator='\n', null=True, blank=True)
    max_file_preview_size = _dj_models.CharField(
        max_length=15,
        choices=tuple((f'{n1},{n2}', f'{n1},{n2}') for n1, n2 in _w_cons.FILE_PREVIEW_SIZES),
        default=f'{_w_cons.FILE_PREVIEW_SIZES[2][0]},{_w_cons.FILE_PREVIEW_SIZES[2][1]}',
    )  # TODO use
    thumbnails_size = _dj_models.IntegerField(validators=[thumbnail_size_validator], default=200)  # TODO use
    show_page_content_in_diffs = _dj_models.BooleanField(default=True)  # TODO use
    show_diff_after_revert = _dj_models.BooleanField(default=True)  # TODO use
    show_hidden_categories = _dj_models.BooleanField(default=False)  # TODO use
    ask_revert_confirmation = _dj_models.BooleanField(default=True)  # TODO use
    uses_editor_syntax_highlighting = _dj_models.BooleanField(default=True)
    mark_all_wiki_edits_as_minor = _dj_models.BooleanField(default=False)
    warn_when_no_wiki_edit_comment = _dj_models.BooleanField(default=True)
    warn_when_wiki_edit_not_published = _dj_models.BooleanField(default=True)
    show_preview_above_edit_form = _dj_models.BooleanField(default=True)  # TODO use
    show_preview_without_reload = _dj_models.BooleanField(default=True)  # TODO use
    days_nb_rc_fl_logs = _dj_models.IntegerField(validators=[days_nb_rc_fl_logs_validator], default=30)  # TODO use
    edits_nb_rc_fl_logs = _dj_models.IntegerField(validators=[edits_nb_rc_fl_logs_validator], default=50)
    group_edits_per_page_rc_fl = _dj_models.BooleanField(default=False)  # TODO use
    mask_wiki_minor_edits = _dj_models.BooleanField(default=False)  # TODO use
    mask_wiki_bot_edits = _dj_models.BooleanField(default=False)  # TODO use
    mask_wiki_own_edits = _dj_models.BooleanField(default=True)  # TODO use
    mask_wiki_anonymous_edits = _dj_models.BooleanField(default=False)  # TODO use
    mask_wiki_authenticated_edits = _dj_models.BooleanField(default=False)  # TODO use
    mask_wiki_categorization_edits = _dj_models.BooleanField(default=False)  # TODO use
    mask_wiki_patrolled_edits = _dj_models.BooleanField(default=False)  # TODO use
    fl_add_created_pages = _dj_models.BooleanField(default=False)
    fl_add_modified_pages = _dj_models.BooleanField(default=False)
    fl_add_renamed_pages = _dj_models.BooleanField(default=False)  # TODO use
    fl_add_deleted_pages = _dj_models.BooleanField(default=False)  # TODO use
    fl_add_reverted_pages = _dj_models.BooleanField(default=False)  # TODO use
    fl_add_created_topics = _dj_models.BooleanField(default=True)  # TODO use
    fl_add_replied_to_topics = _dj_models.BooleanField(default=False)  # TODO use
    search_default_results_nb = _dj_models.IntegerField(validators=[search_results_nb_validator],
                                                        default=20)  # TODO use
    search_mode = _dj_models.CharField(
        max_length=10,
        choices=tuple((sm.value, sm.value) for sm in _se.SearchMode),
        default=_se.SearchMode.DEFAULT.value,
    )  # TODO use
    notif_email_frequency = _dj_models.CharField(
        max_length=15,
        choices=tuple((neu.value, neu.value) for neu in _notif.NotificationEmailFrequency),
        default=_notif.NotificationEmailFrequency.IMMEDIATELY.value,
    )  # TODO use
    html_email_updates = _dj_models.BooleanField(default=True)  # TODO use
    notif_user_talk_edits_email = _dj_models.BooleanField(default=True)  # TODO use
    notif_followed_pages_edits_web = _dj_models.BooleanField(default=True)  # TODO use
    notif_followed_pages_edits_email = _dj_models.BooleanField(default=True)  # TODO use
    notif_talk_mentions_web = _dj_models.BooleanField(default=True)  # TODO use
    notif_talk_mentions_email = _dj_models.BooleanField(default=True)  # TODO use
    notif_message_answers_web = _dj_models.BooleanField(default=True)  # TODO use
    notif_message_answers_email = _dj_models.BooleanField(default=True)  # TODO use
    notif_topic_answers_web = _dj_models.BooleanField(default=True)  # TODO use
    notif_topic_answers_email = _dj_models.BooleanField(default=True)  # TODO use
    notif_thanks_web = _dj_models.BooleanField(default=True)  # TODO use
    notif_thanks_email = _dj_models.BooleanField(default=False)  # TODO use
    notif_failed_connection_attempts_web = _dj_models.BooleanField(default=True)  # TODO use
    notif_failed_connection_attempts_email = _dj_models.BooleanField(default=True)  # TODO use
    notif_permissions_edit_web = _dj_models.BooleanField(default=True)  # TODO use
    notif_permissions_edit_email = _dj_models.BooleanField(default=True)  # TODO use
    notif_user_email_web = _dj_models.BooleanField(default=True)  # TODO use
    notif_cancelled_edits_web = _dj_models.BooleanField(default=True)  # TODO use
    notif_cancelled_edits_email = _dj_models.BooleanField(default=False)  # TODO use
    notif_edit_count_milestones_web = _dj_models.BooleanField(default=True)  # TODO use
    user_notification_blacklist = model_fields.CommaSeparatedStringsField(separator='\n', null=True,
                                                                          blank=True)  # TODO use
    page_notification_blacklist = model_fields.CommaSeparatedStringsField(separator='\n', null=True,
                                                                          blank=True)  # TODO use

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.groups.count() == 0:  # Add default group when saving anonymous user for the first time
            self.groups.add(UserGroup.objects.get(label=_groups.GROUP_ALL))

    def __str__(self):
        return self.username


class UserBlock(_dj_models.Model):
    """Defines the block status of a user.
    Users can be prevented from editing the map/wiki pages, posting messages and editing their own settings.
    Blocks expire after a specified date. If no end date is specified, the block will never expire.
    """
    user = _dj_models.OneToOneField(CustomUser, on_delete=_dj_models.PROTECT, related_name='block')
    end_date = _dj_models.DateTimeField(null=True, blank=True)
    allow_messages_on_own_user_page = _dj_models.BooleanField(default=True)
    allow_editing_own_settings = _dj_models.BooleanField(default=True)

    @property
    def is_active(self):
        return self.end_date and self.end_date > _utils.now()


class IPBlock(_dj_models.Model):
    """Defines the block status of an IP address.
    Non-authenticated users under specific IPs can be prevented from editing pages, posting messages
    and creating new accounts.
    Blocks expire after a specified date. If no end date is specified, the block will never expire.
    """
    ip = _dj_models.CharField(max_length=39)
    end_date = _dj_models.DateTimeField(null=True, blank=True)
    allow_messages_on_own_user_page = _dj_models.BooleanField(default=True)
    allow_account_creation = _dj_models.BooleanField(default=True)

    @property
    def is_active(self):
        return self.end_date and self.end_date > _utils.now()


# Wiki models not in own file as coupling with user-related models is too important
# region Wiki


def future_date_validator(value: _dt.date | _dt.datetime):
    now = _utils.now()
    if isinstance(value, _dt.date):
        now = now.date()
    if value and value <= now:
        raise _dj_exc.ValidationError('date is in the past', code='past_date')


class NonDeletableMixin:
    def delete(self, *args, **kwargs):
        raise RuntimeError(f'cannot delete instances of {self.__class__.__name__}')


class Revision(_dj_models.Model, NonDeletableMixin):
    """Base class for all revision models."""
    date = _dj_models.DateTimeField(auto_now_add=True)
    author = _dj_models.ForeignKey('CustomUser', on_delete=_dj_models.PROTECT)
    comment = _dj_models.CharField(max_length=200, null=True, blank=True)
    comment_hidden = _dj_models.BooleanField(default=False)
    hidden = _dj_models.BooleanField(default=False)
    is_minor = _dj_models.BooleanField(default=False)
    is_bot = _dj_models.BooleanField(default=False)
    tags = _dj_models.ManyToManyField('Tag')

    class Meta:
        abstract = True
        get_latest_by = 'date'
        ordering = ('date',)

    @property
    def bytes_size(self):
        return len(self._get_content()[1].encode(encoding='utf-8'))

    def get_byte_size_diff(self, ignore_hidden: bool):
        if prev := self.get_previous(ignore_hidden):
            return self.bytes_size - prev.bytes_size
        else:
            return self.bytes_size

    def get_next(self, ignore_hidden: bool) -> Revision | None:
        f = _dj_models.Q(date__gt=self.date, **{self._get_object()[0]: self._get_object()[1]})
        if ignore_hidden:
            f &= _dj_models.Q(hidden=False)
        try:
            return self._manager().filter(f).earliest()
        except _dj_models.ObjectDoesNotExist:
            return None

    def get_previous(self, ignore_hidden: bool) -> Revision | None:
        f = _dj_models.Q(date__lt=self.date, **{self._get_object()[0]: self._get_object()[1]})
        if ignore_hidden:
            f &= _dj_models.Q(hidden=False)
        try:
            return self._manager().filter(f).latest()
        except _dj_models.ObjectDoesNotExist:
            return None

    def is_latest(self, ignore_hidden: bool):
        f = _dj_models.Q(date__gt=self.date, **{self._get_object()[0]: self._get_object()[1]})
        if ignore_hidden:
            f &= _dj_models.Q(hidden=False)
        return not self._manager().filter(f).exists()

    def is_first(self, ignore_hidden: bool):
        f = _dj_models.Q(date__lt=self.date, **{self._get_object()[0]: self._get_object()[1]})
        if ignore_hidden:
            f &= _dj_models.Q(hidden=False)
        return not self._manager().filter(f).exists()

    @classmethod
    def _manager(cls) -> _dj_models.Manager:
        return cls.objects

    def _get_object(self) -> tuple[str, _typ.Any]:
        raise NotImplementedError()

    def _get_content(self) -> tuple[str, str]:
        raise NotImplementedError()


# region Pages


def page_namespace_id_validator(value: int):
    if value not in _w_ns.NAMESPACE_IDS.keys():
        raise _dj_exc.ValidationError('invalid namespace ID', code='page_invalid_namespace_id')


def page_title_validator(value: str):
    if _settings.INVALID_TITLE_REGEX.search(value) or value.startswith(' ') or value.endswith(' '):
        raise _dj_exc.ValidationError('invalid page title', code='page_invalid_title')


class Page(_dj_models.Model, NonDeletableMixin):
    """Represents a wiki page."""
    namespace_id = _dj_models.IntegerField(validators=[page_namespace_id_validator])
    title = _dj_models.CharField(max_length=200, validators=[page_title_validator])
    content_type = _dj_models.CharField(max_length=20, choices=tuple((v, v) for v in _w_cons.CONTENT_TYPES.values()),
                                        default=_w_cons.CT_WIKIPAGE)
    deleted = _dj_models.BooleanField(default=False)
    is_category_hidden = _dj_models.BooleanField(null=True, blank=True)
    content_language = _dj_models.ForeignKey(_i18n_m.Language, on_delete=_dj_models.PROTECT,
                                             default=_i18n_m.Language.get_default)

    # Parsed content/cache metadata

    # Page’s parsed content cache or minified CSS/JS/JSON code
    cached_parsed_content = _dj_models.TextField(null=True, blank=True)
    cached_parsed_revision_id = _dj_models.IntegerField(null=True, blank=True)
    parse_time = _dj_models.IntegerField(null=True, blank=True)
    parse_date = _dj_models.DateTimeField(null=True, blank=True)
    cache_expiry_date = _dj_models.DateTimeField(null=True, blank=True)
    size_before_parse = _dj_models.IntegerField(null=True, blank=True)
    size_after_parse = _dj_models.IntegerField(null=True, blank=True)
    # May redirect to non-existent page
    redirects_to_namespace_id = _dj_models.IntegerField(validators=[page_namespace_id_validator], null=True, blank=True)
    redirects_to_title = _dj_models.CharField(max_length=200, validators=[page_title_validator], null=True, blank=True)

    class Meta:
        unique_together = ('namespace_id', 'title')
        ordering = ('namespace_id', 'title')

    def validate_constraints(self, exclude=None):
        super().validate_constraints(exclude=exclude)
        if self.namespace == _w_ns.NS_CATEGORY and self.is_category_hidden is not None:
            raise _dj_exc.ValidationError(
                'page is not a category',
                code='page_not_category'
            )
        if self.namespace.allows_subpages and (
                self.title.startswith('/') or self.title.endswith('/')
                or '//' in self.title or '' in map(str.strip, self.title.split('/'))
        ):
            raise _dj_exc.ValidationError('invalid page title', code='page_invalid_title')

    @property
    def namespace(self) -> _w_ns.Namespace:
        """Page’s namespace."""
        return _w_ns.NAMESPACE_IDS[self.namespace_id]

    @property
    def full_title(self) -> str:
        """Page’s full title in the format "<namespace>:<title>"."""
        return self.namespace.get_full_page_title(self.title)

    @property
    def base_name(self) -> str:
        """Page’s base name. If the namespace allows subpages or is "Special", it is the value before the first '/'."""
        if '/' in self.title and (self.namespace.allows_subpages or self.namespace == _w_ns.NS_SPECIAL):
            return self.title.split('/')[0]
        return self.title

    @property
    def parent_title(self) -> str:
        """Parent page’s title.
        If the namespace allows subpages or is "Special", it is the value before the last '/'."""
        if '/' in self.title and (self.namespace.allows_subpages or self.namespace == _w_ns.NS_SPECIAL):
            return '/'.join(self.title.split('/')[:-1])
        return self.title

    @property
    def page_name(self) -> str:
        """Page’s name. If the namespace allows subpages, it is the value after the last '/'."""
        if '/' in self.title and self.namespace.allows_subpages:
            return self.title.split('/')[-1]
        return self.title

    @property
    def exists(self) -> bool:
        """Whether this pages exists in the database or is a predefined special page."""
        from ..api.wiki import special_pages
        if self.namespace == _w_ns.NS_SPECIAL:
            return special_pages.SPECIAL_PAGES.get(self.base_name) is not None
        return not self.deleted and self.pk is not None

    @property
    def default_sort_key(self) -> str:
        """This page’s default sort key."""
        return self.title

    def can_user_edit(self, user: User) -> bool:
        f"""Check whether the given user can edit this page.

        A user `cannot` edit a page if any of the following conditions is met:
            - They cannot edit the page’s namespace.
            - They are logged in and blocked.
            - They are not logged in and their IP is blocked.
            - The page is a user page but not theirs and they do not have the
                {_perms.PERM_WIKI_EDIT_USER_PAGES} permission.
            - The page is protected an they do not have the {_perms.PERM_WIKI_PROTECT} permission.

        :param user: The user.
        :return: True if the user can edit, false otherwise.
        """
        if not self.namespace.can_user_edit_pages(user):
            return False

        if user.is_blocked:
            return False

        if not user.is_authenticated:
            try:
                ip_block = IPBlock.objects.get(ip=user.ip)
            except IPBlock.DoesNotExist:
                ip_block = None
            if ip_block and ip_block.is_active:
                return False

        try:
            pp = PageProtection.objects.get(page_namespace_id=self.namespace_id, page_title=self.title)
        except PageProtection.DoesNotExist:
            pp = None
        if pp and pp.is_active and not user.is_in_group(pp.protection_level):
            return False

        if (self.namespace == _w_ns.NS_USER
                and self.base_name != user.username
                and not user.has_permission(_perms.PERM_WIKI_EDIT_USER_PAGES)):
            return False

        return True

    def can_user_post_messages(self, user: User) -> bool:
        """Check whether the given user can post messages on this page.

        A user `cannot` post a message if any of the following conditions is met:
            - The namespace is not editable.
            - They are logged in and blocked, and they are not on their user page or cannot post messages on it.
            - They are not logged in and their IP is blocked, and they are not on their user page \
             or cannot post messages on it.

        :param user: The user.
        :return: True if the user can post messages, false otherwise.
        """
        if not self.namespace.is_editable:
            return False

        own_page = self.namespace == _w_ns.NS_USER and self.base_name == user.username
        if user.is_blocked and (not own_page or not user.block.allow_messages_on_own_user_page):
            return False

        if not user.is_authenticated:
            try:
                ip_block = IPBlock.objects.get(ip=user.ip)
            except IPBlock.DoesNotExist:
                ip_block = None
            if ip_block and ip_block.is_active and (not own_page or not ip_block.allow_messages_on_own_user_page):
                return False

        pp = self.get_edit_protection()
        if pp and pp.protect_talks and pp.is_active and not user.is_in_group(pp.protection_level):
            return False

        return True

    def is_user_following(self, user: User) -> bool:
        """Check whether the given agent is following this page, whether it exists or not.

        :param user: The user.
        :return: True if the user follows this page, false otherwise.
        """
        if not user.exists:
            return False
        try:
            follow = user.internal_object.followed_pages.get(
                page_namespace_id=self.namespace_id,
                page_title=self.title,
            )
        except PageFollowStatus.DoesNotExist:
            return False
        return follow.is_active

    def get_latest_revision(self) -> PageRevision | None:
        """Return the latest visible revision of this page."""
        if (self.exists and self.namespace != _w_ns.NS_SPECIAL
                and (revision := self.revisions.filter(hidden=False).latest())):
            return revision
        return None

    def last_revision_date(self) -> _dt.datetime | None:
        """Return the date of the latest visible edit made on this page or None if it does not exist."""
        if r := self.get_latest_revision():
            return r.date
        return None

    def get_content(self) -> str:
        """Return this page’s content or an empty string if it does not exist."""
        if r := self.get_latest_revision():
            return r.content
        return ''

    def get_edit_protection(self) -> PageProtection | None:
        """Return the page protection status for this page if it is protected, None otherwise."""
        try:
            return PageProtection.objects.get(page_namespace_id=self.namespace_id, page_title=self.title)
        except PageProtection.DoesNotExist:
            return None

    def get_redirects(self) -> _dj_models.QuerySet[Page]:
        """Return a query set of all pages that redirect to this page."""
        return Page.objects.filter(redirects_to_namespace_id=self.namespace_id, redirects_to_title=self.title)

    def get_parent_page_titles(self) -> list[tuple[str, str]]:
        """Return the list of titles of this page’s parent pages."""
        if not self.namespace.allows_subpages or '/' not in self.title:
            return []
        parts = self.title.split('/')[:-1]
        titles = []
        buffer = ''
        for i in range(len(parts)):
            if buffer:
                buffer += '/'
            buffer += parts[i]
            titles.append((self.namespace.get_full_page_title(buffer),
                           self.namespace.get_full_page_title(parts[i]) if i == 0 else parts[i]))
        return titles

    def get_subpages(self) -> _dj_models.QuerySet[Page]:
        """Return a query set of all subpages of this page."""
        if not self.namespace.allows_subpages:
            return _dj_auth_models.EmptyManager(Page).all()
        return Page.objects.filter(namespace_id=self.namespace_id, title__startswith=self.title + '/')

    def get_categories(self) -> _dj_models.QuerySet[PageCategory]:
        """Return a query set of all categories of this page"""
        if not self.exists or self.namespace != _w_ns.NS_SPECIAL:
            return _dj_auth_models.EmptyManager(PageCategory).all()
        return PageCategory.objects.filter(page_id=self.id).order_by('page__namespace_id', 'page__title')

    def get_linked_pages(self) -> _dj_models.QuerySet[Page]:
        """Return a query set of all pages linking to this page."""
        return Page.objects.filter(embedded_links__page_namespace_id=self.namespace_id,
                                   embedded_links__page_title=self.title)


class PageCategory(_dj_models.Model):
    """Model that associates a page to a category with an optional sort key.
    Pages can be in non-existent categories.
    """
    page = _dj_models.ForeignKey(Page, on_delete=_dj_models.PROTECT, related_name='categories')
    cat_title = _dj_models.CharField(max_length=200, validators=[page_title_validator])
    sort_key = _dj_models.CharField(max_length=200, null=True, blank=True)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if PageCategory.objects.filter(_dj_models.Q(page=self.page, cat_title=self.cat_title)
                                       & ~_dj_models.Q(id=self.id)).exists():
            raise _dj_exc.ValidationError('duplicate category for page', code='duplicate_category')

    @staticmethod
    def subcategories_for_category(cat_title: str) -> _dj_models.QuerySet[Page]:
        """Get a query set of pages that are subcategories of the given category.

        :param cat_title: Category’s title.
        :return: A QuerySet of Page objects.
        """
        return Page.objects.filter(categories__cat_title=cat_title, namespace_id=_w_ns.NS_CATEGORY.id)

    @staticmethod
    def pages_for_category(cat_title: str) -> _dj_models.QuerySet[Page]:
        """Get a query set of pages that are in the given category.

        :param cat_title: Category’s title.
        :return: A QuerySet of Page objects.
        """
        return Page.objects.filter(_dj_models.Q(categories__cat_title=cat_title)
                                   & ~_dj_models.Q(namespace_id=_w_ns.NS_CATEGORY.id))


class PageLink(_dj_models.Model):
    """Defines a link between two pages."""
    page = _dj_models.ForeignKey(Page, on_delete=_dj_models.PROTECT, related_name='embedded_links')
    # No foreign key to Page as pages may link to non-existent pages.
    page_namespace_id = _dj_models.IntegerField(validators=[page_namespace_id_validator])
    page_title = _dj_models.CharField(max_length=200, validators=[page_title_validator])


class PageProtection(_dj_models.Model):
    """Defines the protection status of a page. Non-existent pages can be protected."""
    # No foreign key to Page as it allows protecting non-existent pages.
    page_namespace_id = _dj_models.IntegerField(validators=[page_namespace_id_validator])
    page_title = _dj_models.CharField(max_length=200, validators=[page_title_validator])
    end_date = _dj_models.DateTimeField(null=True, blank=True)
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)
    protection_level = _dj_models.ForeignKey(UserGroup, on_delete=_dj_models.PROTECT)
    protect_talks = _dj_models.BooleanField(default=False)

    class Meta:
        unique_together = ('page_namespace_id', 'page_title')

    @property
    def is_active(self):
        return not self.end_date or self.end_date > _utils.now()


class PageFollowStatus(_dj_models.Model):
    """Defines the follow status of a page. Non-existent pages can be followed."""
    user = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT, related_name='followed_pages')
    # No foreign key to Page as it allows following non-existent pages.
    page_namespace_id = _dj_models.IntegerField(validators=[page_namespace_id_validator])
    page_title = _dj_models.CharField(max_length=200, validators=[page_title_validator])
    end_date = _dj_models.DateTimeField(null=True, blank=True)

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        if PageFollowStatus.objects.filter(
                _dj_models.Q(user=self.user, page_namespace_id=self.page_namespace_id, page_title=self.page_title)
                & ~_dj_models.Q(id=self.id)).exists():
            raise _dj_exc.ValidationError(
                'duplicate follow list entry',
                code='page_follow_list_duplicate_entry'
            )

    @property
    def is_active(self):
        return not self.end_date or self.end_date > _utils.now()


def tag_label_validator(value: str):
    if not value.isascii() or not value.isalnum():
        raise _dj_exc.ValidationError('invalid tag label', code='tag_invalid_label')


class Tag(_dj_models.Model):
    """Tags are used to add metadata to page revisions."""
    label = _dj_models.CharField(max_length=20, validators=[tag_label_validator])


# endregion
# region Discussions


class Topic(_dj_models.Model, NonDeletableMixin):
    """A talk topic groups a hierarchical list of user messages."""
    page = _dj_models.ForeignKey(Page, on_delete=_dj_models.PROTECT, related_name='topics')
    author = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT, related_name='wiki_topics')
    date = _dj_models.DateTimeField(auto_now_add=True)
    deleted = _dj_models.BooleanField(default=False)

    def get_title(self) -> str:
        """Return the title of this topic or an empty string if it does not exist."""
        return revision.title if (revision := self.revisions.latest()) else ''


class Message(_dj_models.Model, NonDeletableMixin):
    """Messages can be posted by users under specific topics."""
    topic = _dj_models.ForeignKey(Topic, on_delete=_dj_models.PROTECT, related_name='messages')
    author = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT, related_name='wiki_messages')
    date = _dj_models.DateTimeField(auto_now_add=True)
    response_to = _dj_models.ForeignKey('self', on_delete=_dj_models.PROTECT, related_name='responses', null=True)
    deleted = _dj_models.BooleanField(default=False)

    def get_content(self) -> str:
        """Return the content of this message or an empty string if it does not exist."""
        return revision.text if (revision := self.revisions.latest()) else ''


# endregion
# region Revisions


class PageRevision(Revision):
    """A page revision is a version of a page’s content at a given time."""
    page = _dj_models.ForeignKey(Page, on_delete=_dj_models.PROTECT, related_name='revisions')
    content = _dj_models.TextField()
    page_creation = _dj_models.BooleanField()

    def _get_object(self) -> tuple[str, _typ.Any]:
        return 'page', self.page

    def _get_content(self) -> tuple[str, str]:
        return 'content', self.content


class TopicRevision(Revision):
    """A topic revision is a version of a topic’s title at a given time."""
    topic = _dj_models.ForeignKey(Topic, on_delete=_dj_models.PROTECT, related_name='revisions')
    title = _dj_models.CharField(max_length=200)

    def _get_object(self) -> tuple[str, _typ.Any]:
        return 'topic', self.topic

    def _get_content(self) -> tuple[str, str]:
        return 'title', self.title


class MessageRevision(Revision):
    """A message revision is a version of a message’s content at a given time."""
    message = _dj_models.ForeignKey(Message, on_delete=_dj_models.PROTECT, related_name='revisions')
    text = _dj_models.TextField()

    def _get_object(self) -> tuple[str, _typ.Any]:
        return 'message', self.message

    def _get_content(self) -> tuple[str, str]:
        return 'text', self.text


# endregion
# region Logs


class Log(_dj_models.Model, NonDeletableMixin):
    """Base class for logs. Logs are models that store all operations performed by users."""
    date = _dj_models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class PageLog(Log):
    """Base class for page-related operations."""
    performer = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT)
    page = _dj_models.ForeignKey(Page, on_delete=_dj_models.PROTECT)

    class Meta:
        abstract = True


class PageCreationLog(PageLog):
    """New entries are added each time a page is created."""

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class PageDeletionLog(PageLog):
    """New entries are added each time a page is deleted."""
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class PageProtectionLog(Log):
    """New entries are added each time a page’s protection status changes."""
    performer = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT)
    page_namespace_id = _dj_models.IntegerField(validators=[page_namespace_id_validator])
    page_title = _dj_models.CharField(max_length=200, validators=[page_title_validator])
    end_date = _dj_models.DateTimeField(null=True, blank=True)
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)
    protection_level = _dj_models.ForeignKey(UserGroup, on_delete=_dj_models.PROTECT)
    protect_talks = _dj_models.BooleanField()

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class PageRenameLog(PageLog):
    """New entries are added each time a page is renamed."""
    old_title = _dj_models.CharField(max_length=200, validators=[page_title_validator])
    new_title = _dj_models.CharField(max_length=200, validators=[page_title_validator])
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)
    leave_redirect = _dj_models.BooleanField()

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class PageContentLanguageLog(PageLog):
    """New entries are added each time the content language of a page is modified."""
    language = _dj_models.ForeignKey(_i18n_m.Language, on_delete=_dj_models.PROTECT)
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class PageContentTypeLog(PageLog):
    """New entries are added each time the content type of a page is modified."""
    content_type = _dj_models.CharField(max_length=20, choices=tuple((v, v) for v in _w_cons.CONTENT_TYPES.values()))
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class PageRevisionMaskLog(Log):
    """New entries are added each time a page revision is masked or unmasked."""
    MASK_FULLY = 'mask_fully'
    MASK_COMMENTS_ONLY = 'mask_comments_only'
    UNMASK_ALL = 'unmask_all'
    UNMASK_ALL_BUT_COMMENTS = 'unmask_all_but_comments'

    performer = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT)
    revision = _dj_models.ForeignKey(PageRevision, on_delete=_dj_models.PROTECT)
    action = _dj_models.CharField(max_length=30, choices=(
        (MASK_FULLY, MASK_FULLY),
        (MASK_COMMENTS_ONLY, MASK_COMMENTS_ONLY),
        (UNMASK_ALL, UNMASK_ALL),
        (UNMASK_ALL_BUT_COMMENTS, UNMASK_ALL_BUT_COMMENTS),
    ))
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class UserLog(Log):
    """Base class for user-related operations."""
    user = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT)

    class Meta:
        abstract = True


class UserAccountCreationLog(UserLog):
    """New entries are added each time a user account is created."""

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class UserMaskLog(UserLog):
    """New entries are added each time a user account is created."""
    performer = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT,
                                      related_name='usermasklog_performer_set')
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)
    masked = _dj_models.BooleanField()

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class UserRenameLog(UserLog):
    """New entries are added each time a user is renamed."""
    performer = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT,
                                      related_name='userrenamelog_performer_set')
    old_username = _dj_models.CharField(max_length=150, validators=[username_validator])
    new_username = _dj_models.CharField(max_length=150, validators=[username_validator])
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class UserGroupLog(UserLog):
    """New entries are added each time a user account is created."""
    performer = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT,
                                      related_name='usergrouplog_performer_set',
                                      null=True, blank=True)
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)
    joined = _dj_models.BooleanField()
    group = _dj_models.ForeignKey(UserGroup, on_delete=_dj_models.PROTECT)

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class UserBlockLog(UserLog):
    """New entries are added each time a user’s block status changes."""
    performer = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT,
                                      related_name='userblocklog_performer_set')
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)
    end_date = _dj_models.DateTimeField(null=True, blank=True)
    allow_messages_on_own_user_page = _dj_models.BooleanField()
    allow_editing_own_settings = _dj_models.BooleanField()
    blocked = _dj_models.BooleanField()

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)


class IPBlockLog(Log):
    """New entries are added each time an IP address’ block status changes."""
    performer = _dj_models.ForeignKey(CustomUser, on_delete=_dj_models.PROTECT)
    reason = _dj_models.CharField(max_length=200, null=True, blank=True)
    end_date = _dj_models.DateTimeField(null=True, blank=True)
    allow_messages_on_own_user_page = _dj_models.BooleanField()
    ip = _dj_models.CharField(max_length=39)
    allow_account_creation = _dj_models.BooleanField()

    class Meta:
        get_latest_by = 'date'
        ordering = ('date',)

# endregion
# endregion
