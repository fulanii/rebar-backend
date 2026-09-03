"""
Background jobs.

The suite runs with `CELERY_TASK_ALWAYS_EAGER`, so `.delay()` executes inline and the
existing email assertions keep working. What is tested here is the part eager mode
does not make obvious: that work is handed over rather than done in the request, and
that a failing job cannot take the request down with it.
"""

from unittest.mock import patch

import pytest
from django.urls import reverse

from authentication.tasks import EmailNotDelivered, send_email

pytestmark = pytest.mark.django_db


class TestSendEmailTask:
    def test_it_is_registered_under_a_stable_name(self):
        """Queued jobs name the task as a string, so renaming the module orphans them."""
        assert send_email.name == "authentication.tasks.send_email"

    def test_a_delivered_email_returns_true(self, block_outbound_email, settings):
        settings.EMAIL_PROVIDER = "brevo"

        assert send_email.run("jane@example.com", "3", {"FIRST_NAME": "Jane"}) is True
        assert block_outbound_email.called

    def test_a_refused_email_raises_for_the_retry(self, block_outbound_email, settings):
        settings.EMAIL_PROVIDER = "brevo"
        block_outbound_email.brevo_send.side_effect = Exception("brevo is down")

        with pytest.raises(EmailNotDelivered):
            send_email.run("jane@example.com", "3", {})

    def test_arguments_are_json_serializable(self, block_outbound_email, settings):
        """
        A worker is a separate process: anything not JSON cannot cross to it.

        `CELERY_TASK_SERIALIZER` is json, so a model instance or a datetime passed here
        would fail at queue time in production and pass silently under eager mode.
        """
        import json

        settings.EMAIL_PROVIDER = "brevo"
        send_email.delay("jane@example.com", "3", {"FIRST_NAME": "Jane", "EXPIRY_MINUTES": 15})

        args = block_outbound_email.brevo_send.call_args
        json.dumps([args.kwargs["template_id"], args.kwargs["params"]])


class TestWorkIsHandedOver:
    def test_registration_queues_the_email(self, api_client):
        with patch("authentication.tasks.send_email") as queued:
            response = api_client.post(
                reverse("register"),
                {
                    "email": "new@example.com",
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "phone_number": "5551234567",
                    "password": "SecurePass123!",
                    "confirm_password": "SecurePass123!",
                },
                format="json",
            )

        assert response.status_code == 201
        assert queued.call_count == 1

    def test_the_request_does_not_wait_on_the_provider(self, api_client):
        """
        The point of the queue: a slow or dead provider must not slow down a signup.

        With the task patched out, nothing in the request path touches the provider.
        """
        with patch("authentication.tasks.send_email.delay"), patch("brevo.Brevo") as brevo:
            api_client.post(reverse("password-reset-request"), {"email": "nobody@example.com"}, format="json")

        assert brevo.called is False

    def test_a_dead_provider_does_not_fail_the_request(self, api_client, block_outbound_email, settings):
        """
        `CELERY_TASK_EAGER_PROPAGATES` is off, which is what makes this true without a
        broker as well as with one. Turning it on would let a provider outage 500 a
        registration in development.
        """
        settings.EMAIL_PROVIDER = "brevo"
        block_outbound_email.brevo_send.side_effect = Exception("brevo is down")

        response = api_client.post(
            reverse("register"),
            {
                "email": "new@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "phone_number": "5551234567",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
            format="json",
        )

        assert response.status_code == 201


class TestEagerModeConfiguration:
    def test_the_suite_never_needs_a_broker(self, settings):
        assert settings.CELERY_TASK_ALWAYS_EAGER is True

    def test_a_failing_job_is_captured_not_raised(self, settings):
        assert settings.CELERY_TASK_EAGER_PROPAGATES is False

    def test_retries_are_off_under_test(self, settings):
        """Otherwise every provider-failure test would run the task four times."""
        assert settings.EMAIL_MAX_RETRIES == 0
