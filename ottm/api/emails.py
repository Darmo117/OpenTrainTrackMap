"""This module defines functions to send emails."""
import django.core.mail as _dj_mail

from .. import models as _models


def send_email(user: _models.User, subject: str, message_plain: str, message_html: str) -> bool:
    """Send an email to the specifiec user.

    :param user: The user to send the email to.
    :param subject: Email’s subject.
    :param message_plain: Email’s plain text content.
    :param message_html: Email’s HTML content.
    :return: Whether the email was successfully sent.
    """
    if not user.is_authenticated:
        return False
    return _dj_mail.send_mail(subject, message_plain, None, [user.email], html_message=message_html) != 0
