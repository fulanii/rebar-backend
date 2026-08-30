"""The one-time code base class: hashing, expiry, single use, attempt limit."""

from datetime import timedelta

import pytest
from django.utils import timezone

from authentication.models import EmailChange, EmailVerification, PasswordReset
from authentication.models.one_time_code import MAX_ATTEMPTS

pytestmark = pytest.mark.django_db


class TestCodeHashing:
    def test_raw_code_is_never_stored(self, base_user):
        verification = EmailVerification(user=base_user)
        verification.set_code("123456")

        assert verification.code != "123456"
        assert "123456" not in verification.code

    def test_check_code_accepts_the_right_code(self, base_user):
        verification = EmailVerification(user=base_user)
        verification.set_code("123456")

        assert verification.check_code("123456") is True

    def test_check_code_rejects_the_wrong_code(self, base_user):
        verification = EmailVerification(user=base_user)
        verification.set_code("123456")

        assert verification.check_code("654321") is False

    def test_same_code_hashes_differently_for_two_users(self, base_user, second_user):
        first = EmailVerification(user=base_user)
        first.set_code("123456")
        second = EmailVerification(user=second_user)
        second.set_code("123456")

        assert first.code != second.code


class TestCodeValidity:
    def test_a_fresh_code_is_valid(self, base_user):
        verification = EmailVerification.objects.create(user=base_user, code="x")

        assert verification.is_expired is False
        assert verification.is_valid is True

    def test_an_expired_code_is_not_valid(self, base_user):
        verification = EmailVerification.objects.create(
            user=base_user,
            code="x",
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        assert verification.is_expired is True
        assert verification.is_valid is False

    def test_a_used_code_is_not_valid(self, base_user):
        verification = EmailVerification.objects.create(user=base_user, code="x")
        verification.mark_used()

        assert verification.used is True
        assert verification.used_at is not None
        assert verification.is_valid is False

    def test_default_expiry_is_fifteen_minutes(self, base_user):
        verification = EmailVerification.objects.create(user=base_user, code="x")
        remaining = verification.expires_at - timezone.now()

        assert timedelta(minutes=14) < remaining <= timedelta(minutes=15)


class TestOneRowPerUser:
    def test_each_model_has_its_own_table(self, base_user):
        EmailVerification.objects.create(user=base_user, code="a")
        PasswordReset.objects.create(user=base_user, code="b")
        EmailChange.objects.create(user=base_user, code="c", new_email="new@example.com")

        assert EmailVerification.objects.filter(user=base_user).count() == 1
        assert PasswordReset.objects.filter(user=base_user).count() == 1
        assert EmailChange.objects.filter(user=base_user).count() == 1


class TestEmailChange:
    def test_it_carries_the_pending_address(self, base_user):
        change = EmailChange.objects.create(user=base_user, code="x", new_email="new@example.com")

        assert change.new_email == "new@example.com"

    def test_it_inherits_the_attempt_limit(self, base_user):
        change = EmailChange.objects.create(user=base_user, code="x", new_email="new@example.com")

        for _ in range(MAX_ATTEMPTS):
            change.register_failure()

        assert change.is_valid is False

    def test_deleting_the_user_deletes_the_row(self, base_user):
        EmailChange.objects.create(user=base_user, code="x", new_email="new@example.com")
        base_user.delete()

        assert EmailChange.objects.exists() is False


class TestAttemptLimit:
    def test_a_fresh_code_has_no_attempts(self, base_user):
        verification = EmailVerification.objects.create(user=base_user, code="x")

        assert verification.attempts == 0
        assert verification.is_exhausted is False

    def test_a_failure_is_counted(self, base_user):
        verification = EmailVerification.objects.create(user=base_user, code="x")
        verification.register_failure()
        verification.refresh_from_db()

        assert verification.attempts == 1
        assert verification.is_valid is True

    def test_the_code_survives_up_to_the_limit(self, base_user):
        verification = EmailVerification.objects.create(user=base_user, code="x")

        for _ in range(MAX_ATTEMPTS - 1):
            assert verification.register_failure() is False

        assert verification.is_valid is True

    def test_the_last_failure_burns_the_code(self, base_user):
        verification = EmailVerification.objects.create(user=base_user, code="x")

        for _ in range(MAX_ATTEMPTS - 1):
            verification.register_failure()

        assert verification.register_failure() is True

        verification.refresh_from_db()
        assert verification.attempts == MAX_ATTEMPTS
        assert verification.used is True
        assert verification.used_at is not None
        assert verification.is_exhausted is True
        assert verification.is_valid is False

    def test_password_resets_count_attempts_too(self, base_user):
        reset = PasswordReset.objects.create(user=base_user, code="x")

        for _ in range(MAX_ATTEMPTS):
            reset.register_failure()

        assert reset.is_valid is False
