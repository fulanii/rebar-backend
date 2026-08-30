"""Brevo provider. Template ids are integers."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send(to_email, template_id, variables):
    """Send `template_id` through Brevo. True on success, False on any failure."""
    if not settings.BREVO_API_KEY:
        logger.warning("event=email_not_sent reason=no_api_key provider=brevo to=%s", to_email)
        return False

    try:
        template_id = int(template_id)
    except (TypeError, ValueError):
        logger.error(
            "event=email_not_sent reason=template_id_not_an_integer provider=brevo value=%r",
            template_id,
        )
        return False

    try:
        from brevo import Brevo, SendTransacEmailRequestToItem
    except ImportError:
        logger.error("event=email_not_sent reason=brevo_not_installed hint='pip install brevo-python'")
        return False

    try:
        client = Brevo(api_key=settings.BREVO_API_KEY)
        result = client.transactional_emails.send_transac_email(
            template_id=template_id,
            params=variables,
            to=[SendTransacEmailRequestToItem(email=to_email)],
        )
    except Exception:
        logger.exception("event=email_failed provider=brevo to=%s template=%s", to_email, template_id)
        return False

    logger.info(
        "event=email_sent provider=brevo to=%s template=%s message_id=%s",
        to_email,
        template_id,
        getattr(result, "message_id", None),
    )
    return True
