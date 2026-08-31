"""Background jobs. One task per kind of slow work. See docs/background-jobs.md."""

import logging

from celery import shared_task
from django.conf import settings

from authentication.utils.email import deliver

logger = logging.getLogger(__name__)


class EmailNotDelivered(Exception):
    """The provider refused or failed. Retryable, unlike a missing template id."""


@shared_task(
    bind=True,
    autoretry_for=(EmailNotDelivered,),
    retry_backoff=30,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_email(self, to_email, template_id, variables):
    """
    Hand one templated email to the provider, retrying a few times if it will not go.

    Arguments are plain JSON, never a model instance: the worker is a separate process
    that may pick this up seconds later, so anything passed by value must still make
    sense then. Never put a raw code in a log line from here.
    """
    self.max_retries = settings.EMAIL_MAX_RETRIES

    if deliver(to_email, template_id, variables):
        return True

    raise EmailNotDelivered(f"template={template_id}")
