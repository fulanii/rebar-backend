"""The one-time code base class: hashing, expiry, single use."""

from datetime import timedelta

import pytest
from django.utils import timezone

from authentication.models import EmailVerification, PasswordReset

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

        assert EmailVerification.objects.filter(user=base_user).count() == 1
        assert PasswordReset.objects.filter(user=base_user).count() == 1
