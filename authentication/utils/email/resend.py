"""Resend provider. Template ids are strings."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send(to_email, template_id, variables):
    """Send `template_id` through Resend. True on success, False on any failure."""
    if not settings.RESEND_API_KEY:
        logger.warning("event=email_not_sent reason=no_api_key provider=resend to=%s", to_email)
        return False

    try:
        import resend
    except ImportError:
        logger.error("event=email_not_sent reason=resend_not_installed hint='pip install resend'")
        return False

    resend.api_key = settings.RESEND_API_KEY

    try:
        resend.Emails.send(
            {
                "to": [to_email],
                "template": {"id": template_id, "variables": variables},
            }
        )
    except Exception:
        logger.exception("event=email_failed provider=resend to=%s template=%s", to_email, template_id)
        return False

    logger.info("event=email_sent provider=resend to=%s template=%s", to_email, template_id)
    return True
