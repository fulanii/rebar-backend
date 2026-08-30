"""The email senders: which provider runs, and what it is handed."""

import pytest

from authentication.utils import (
    send_email_change_email,
    send_password_changed_email,
    send_password_reset_email,
    send_verification_email,
)
from authentication.utils.email import CODE_EXPIRY_MINUTES


@pytest.fixture(autouse=True)
def email_configured(settings):
    settings.BREVO_API_KEY = "brevo-test-key"
    settings.RESEND_API_KEY = "resend-test-key"
    settings.VERIFICATION_TEMPLATE_ID = "3"
    settings.PASSWORD_RESET_TEMPLATE_ID = "4"
    settings.PASSWORD_CHANGED_TEMPLATE_ID = "5"
    settings.EMAIL_CHANGE_TEMPLATE_ID = "6"
    return settings


@pytest.fixture
def brevo(settings):
    settings.EMAIL_PROVIDER = "brevo"


@pytest.fixture
def resend(settings):
    settings.EMAIL_PROVIDER = "resend"
    settings.VERIFICATION_TEMPLATE_ID = "tmpl_verify"
    settings.PASSWORD_RESET_TEMPLATE_ID = "tmpl_reset"


class TestBrevo:
    def test_sends_through_the_verification_template(self, brevo, block_outbound_email):
        send_verification_email("jane@example.com", "Jane", "004821")

        kwargs = block_outbound_email.brevo_send.call_args.kwargs
        assert kwargs["template_id"] == 3
        assert kwargs["to"][0].email == "jane@example.com"

    def test_template_id_is_coerced_to_an_integer(self, brevo, block_outbound_email):
        send_verification_email("jane@example.com", "Jane", "004821")

        assert isinstance(block_outbound_email.brevo_send.call_args.kwargs["template_id"], int)

    def test_a_non_numeric_template_id_is_refused(self, brevo, settings, block_outbound_email):
        settings.VERIFICATION_TEMPLATE_ID = "tmpl_verify"

        assert send_verification_email("jane@example.com", "Jane", "004821") is False
        assert not block_outbound_email.called

    def test_sends_the_documented_variables(self, brevo, block_outbound_email):
        send_verification_email("jane@example.com", "Jane", "004821")

        assert block_outbound_email.brevo_send.call_args.kwargs["params"] == {
            "FIRST_NAME": "Jane",
            "CODE": "004821",
            "EXPIRY_MINUTES": CODE_EXPIRY_MINUTES,
        }

    def test_password_reset_uses_its_own_template(self, brevo, block_outbound_email):
        send_password_reset_email("jane@example.com", "Jane", "123456")

        assert block_outbound_email.brevo_send.call_args.kwargs["template_id"] == 4

    def test_missing_api_key_sends_nothing(self, brevo, settings, block_outbound_email):
        settings.BREVO_API_KEY = ""

        assert send_verification_email("jane@example.com", "Jane", "004821") is False
        assert not block_outbound_email.called

    def test_a_provider_failure_is_swallowed(self, brevo, block_outbound_email):
        block_outbound_email.brevo_send.side_effect = Exception("brevo is down")

        assert send_verification_email("jane@example.com", "Jane", "004821") is False


class TestResend:
    def test_sends_through_the_verification_template(self, resend, block_outbound_email):
        send_verification_email("jane@example.com", "Jane", "004821")

        payload = block_outbound_email.resend.call_args[0][0]
        assert payload["template"]["id"] == "tmpl_verify"
        assert payload["to"] == ["jane@example.com"]

    def test_sends_the_documented_variables(self, resend, block_outbound_email):
        send_verification_email("jane@example.com", "Jane", "004821")

        assert block_outbound_email.resend.call_args[0][0]["template"]["variables"] == {
            "FIRST_NAME": "Jane",
            "CODE": "004821",
            "EXPIRY_MINUTES": CODE_EXPIRY_MINUTES,
        }

    def test_no_html_or_subject_is_sent(self, resend, block_outbound_email):
        send_verification_email("jane@example.com", "Jane", "004821")

        payload = block_outbound_email.resend.call_args[0][0]
        assert "html" not in payload
        assert "subject" not in payload

    def test_password_reset_uses_its_own_template(self, resend, block_outbound_email):
        send_password_reset_email("jane@example.com", "Jane", "123456")

        assert block_outbound_email.resend.call_args[0][0]["template"]["id"] == "tmpl_reset"

    def test_missing_api_key_sends_nothing(self, resend, settings, block_outbound_email):
        settings.RESEND_API_KEY = ""

        assert send_verification_email("jane@example.com", "Jane", "004821") is False
        assert not block_outbound_email.called

    def test_a_provider_failure_is_swallowed(self, resend, block_outbound_email):
        block_outbound_email.resend.side_effect = Exception("resend is down")

        assert send_verification_email("jane@example.com", "Jane", "004821") is False


class TestSharedBehaviour:
    def test_the_code_stays_a_string(self, brevo, block_outbound_email):
        send_verification_email("jane@example.com", "Jane", "004821")

        code = block_outbound_email.brevo_send.call_args.kwargs["params"]["CODE"]
        assert isinstance(code, str)
        assert code == "004821"

    def test_expiry_matches_the_model(self, brevo, block_outbound_email):
        from authentication.models import CODE_LIFETIME

        send_verification_email("jane@example.com", "Jane", "004821")

        params = block_outbound_email.brevo_send.call_args.kwargs["params"]
        assert params["EXPIRY_MINUTES"] == CODE_LIFETIME.total_seconds() // 60

    def test_no_template_id_sends_nothing(self, brevo, settings, block_outbound_email):
        settings.VERIFICATION_TEMPLATE_ID = ""

        assert send_verification_email("jane@example.com", "Jane", "004821") is False
        assert not block_outbound_email.called

    def test_an_unknown_provider_sends_nothing(self, settings, block_outbound_email):
        settings.EMAIL_PROVIDER = "mailgun"

        assert send_verification_email("jane@example.com", "Jane", "004821") is False
        assert not block_outbound_email.called


class TestPasswordChangedEmail:
    def test_uses_its_own_template(self, base_user, settings, block_outbound_email):
        send_password_changed_email(base_user.email, base_user.first_name)

        assert block_outbound_email.brevo_send.call_args.kwargs["template_id"] == int(
            settings.PASSWORD_CHANGED_TEMPLATE_ID
        )

    def test_sends_the_first_name_and_no_code(self, base_user, block_outbound_email):
        send_password_changed_email(base_user.email, base_user.first_name)

        params = block_outbound_email.brevo_send.call_args.kwargs["params"]
        assert params == {"FIRST_NAME": base_user.first_name}

    def test_without_a_template_id_nothing_is_sent(self, base_user, settings, block_outbound_email):
        settings.PASSWORD_CHANGED_TEMPLATE_ID = ""

        assert send_password_changed_email(base_user.email, base_user.first_name) is False
        assert block_outbound_email.called is False


class TestEmailChangeEmail:
    def test_uses_its_own_template(self, base_user, settings, block_outbound_email):
        send_email_change_email("new@example.com", base_user.first_name, "123456")

        assert block_outbound_email.brevo_send.call_args.kwargs["template_id"] == int(settings.EMAIL_CHANGE_TEMPLATE_ID)

    def test_carries_the_code_and_expiry(self, base_user, block_outbound_email):
        send_email_change_email("new@example.com", base_user.first_name, "123456")

        params = block_outbound_email.brevo_send.call_args.kwargs["params"]
        assert params["CODE"] == "123456"
        assert params["EXPIRY_MINUTES"] == 15
