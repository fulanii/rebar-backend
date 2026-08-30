"""
Transactional email.

The provider is chosen by `EMAIL_PROVIDER`; each one lives in its own module beside
this file and exposes the same `send(to_email, template_id, variables)`. The copy and
design of every email live in that provider's dashboard, not here.

See docs/email-templates.md.
"""

import logging

from django.conf import settings

from authentication.models.one_time_code import CODE_LIFETIME

from . import brevo, resend

logger = logging.getLogger(__name__)

CODE_EXPIRY_MINUTES = int(CODE_LIFETIME.total_seconds() // 60)

PROVIDERS = {
    "brevo": brevo.send,
    "resend": resend.send,
}


def _send(to_email, template_id, variables):
    """Dispatch to the configured provider. True on success, False on any failure."""
    send = PROVIDERS.get(settings.EMAIL_PROVIDER)

    if send is None:
        logger.error(
            "event=email_not_sent reason=unknown_provider provider=%s known=%s",
            settings.EMAIL_PROVIDER,
            ",".join(PROVIDERS),
        )
        return False

    if not template_id:
        logger.error("event=email_not_sent reason=no_template_id to=%s", to_email)
        return False

    return send(to_email, template_id, variables)


def send_verification_email(to_email, first_name, code):
    """
    Email a newly registered user the code that activates their account.

    Template: `VERIFICATION_TEMPLATE_ID`
    Variables: `FIRST_NAME`, `CODE`, `EXPIRY_MINUTES`
    """
    return _send(
        to_email,
        template_id=settings.VERIFICATION_TEMPLATE_ID,
        variables={
            "FIRST_NAME": first_name,
            "CODE": code,
            "EXPIRY_MINUTES": CODE_EXPIRY_MINUTES,
        },
    )


def send_password_reset_email(to_email, first_name, code):
    """
    Email a user the code that authorizes a password reset.

    Template: `PASSWORD_RESET_TEMPLATE_ID`
    Variables: `FIRST_NAME`, `CODE`, `EXPIRY_MINUTES`
    """
    return _send(
        to_email,
        template_id=settings.PASSWORD_RESET_TEMPLATE_ID,
        variables={
            "FIRST_NAME": first_name,
            "CODE": code,
            "EXPIRY_MINUTES": CODE_EXPIRY_MINUTES,
        },
    )


def send_password_changed_email(to_email, first_name):
    """
    Tell a user their password just changed, so a change they did not make is visible.

    Template: `PASSWORD_CHANGED_TEMPLATE_ID`
    Variables: `FIRST_NAME`
    """
    return _send(
        to_email,
        template_id=settings.PASSWORD_CHANGED_TEMPLATE_ID,
        variables={"FIRST_NAME": first_name},
    )


def send_email_change_email(to_email, first_name, code):
    """
    Email the code that moves an account to this address. Sent to the **new** address.

    Template: `EMAIL_CHANGE_TEMPLATE_ID`
    Variables: `FIRST_NAME`, `CODE`, `EXPIRY_MINUTES`
    """
    return _send(
        to_email,
        template_id=settings.EMAIL_CHANGE_TEMPLATE_ID,
        variables={
            "FIRST_NAME": first_name,
            "CODE": code,
            "EXPIRY_MINUTES": CODE_EXPIRY_MINUTES,
        },
    )
