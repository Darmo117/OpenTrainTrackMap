"""This module defines functions to send emails."""
import django.core.mail as _dj_mail

from .. import models as _models, settings as _settings

DEFAULT_SUBJECT = f'{_settings.SITE_NAME} email'

TEMPLATE_USER = 'user'
TEMPLATE_USER_COPY = 'user_copy'


def user_send_email(recipient: _models.User, subject: str, content: str, sender: _models.User, is_copy: bool) \
        -> tuple[bool, str | None]:
    """Send an email to the specified user.

    :param recipient: The user to send the email to.
    :param subject: Email’s subject.
    :param content: Email’s plain text content.
    :param sender: The user sending the email.
    :param is_copy: Whether the email is a copy.
    :return: A tuple containing a bool indicating whether the email was successfully sent and an error message if not.
    """
    content_html = _get_email_html_template(recipient, sender, content,
                                            TEMPLATE_USER_COPY if is_copy else TEMPLATE_USER)
    if is_copy:
        subject = f'{subject} [copy]'
    return _send_email(sender if is_copy else recipient, subject, content, content_html, None if is_copy else sender)


def _send_email(recipient: _models.User, subject: str, message_plain: str, message_html: str,
                sender: _models.User = None) -> tuple[bool, str | None]:
    """Send an email to the specified user.

    The message’s plain or HTML version will be selected based on the recipient’s preferences.

    :param recipient: The user to send the email to.
    :param subject: Email’s subject.
    :param message_plain: Email’s content as plain text.
    :param message_html: Email’s content as HTML.
    :param sender: The user sending the email.
    :return: A tuple containing a bool indicating whether the email was successfully sent and an error message if not.
    """
    if sender and not sender.can_send_emails_to(recipient):
        return False, 'cannot_send_email'
    content = message_html if recipient.html_email_updates else message_plain
    email = _dj_mail.EmailMessage(subject, content, to=[recipient.email], reply_to=[sender.email] if sender else None)
    email.content_subtype = 'html' if recipient.html_email_updates else 'plain'
    sent = email.send() == 1
    return sent, None if sent else 'email_error'


def _get_email_html_template(recipient: _models.User, sender: _models.User, message_plain: str,
                             template_name: str) -> str:
    return message_plain  # TODO
