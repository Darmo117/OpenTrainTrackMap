"""This module defines functions to send emails."""
import django.core.mail as _dj_mail

from .. import models as _models, settings as _settings

DEFAULT_SUBJECT = f'{_settings.SITE_NAME} email'


def send_email(user: _models.User, subject: str, message_plain: str,
               message_html: str = None, sender: _models.User = None) -> bool:
    """Send an email to the specifiec user.

    :param user: The user to send the email to.
    :param subject: Email’s subject.
    :param message_plain: Email’s plain text content.
    :param message_html: Email’s HTML content. Optional.
    :param sender: The user sending the email.
    :return: Whether the email was successfully sent.
    """
    if sender and not user.can_send_emails_to(sender):
        return False
    return _dj_mail.send_mail(subject, message_plain, from_email=sender.email if sender else None,
                              recipient_list=[user.email], html_message=message_html) == 1
