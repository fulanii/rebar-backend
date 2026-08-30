"""Issuing one-time codes: exactly one live code per user, per model."""

from datetime import timedelta

import pytest
from django.utils import timezone

from authentication.models import EmailVerification, PasswordReset
from authentication.models.one_time_code import MAX_ATTEMPTS
from authentication.utils import issue_code

pytestmark = pytest.mark.django_db


class TestIssueCode:
    def test_returns_six_digits(self, base_user):
        assert len(issue_code(EmailVerification, base_user)) == 6
        assert issue_code(EmailVerification, base_user).isdigit()

    def test_stores_only_a_hash(self, base_user):
        raw = issue_code(EmailVerification, base_user)
        stored = EmailVerification.objects.get(user=base_user).code

        assert stored != raw
        assert raw not in stored

    def test_the_stored_hash_matches_the_returned_code(self, base_user):
        raw = issue_code(EmailVerification, base_user)

        assert EmailVerification.objects.get(user=base_user).check_code(raw) is True

    def test_only_one_row_per_user(self, base_user):
        issue_code(EmailVerification, base_user)
        issue_code(EmailVerification, base_user)

        assert EmailVerification.objects.filter(user=base_user).count() == 1

    def test_a_new_code_invalidates_the_previous_one(self, base_user):
        first = issue_code(EmailVerification, base_user)
        issue_code(EmailVerification, base_user)

        assert EmailVerification.objects.get(user=base_user).check_code(first) is False

    def test_reissuing_clears_a_consumed_code(self, base_user):
        issue_code(EmailVerification, base_user)
        EmailVerification.objects.get(user=base_user).mark_used()

        issue_code(EmailVerification, base_user)
        reissued = EmailVerification.objects.get(user=base_user)

        assert reissued.used is False
        assert reissued.used_at is None
        assert reissued.is_valid is True

    def test_reissuing_clears_the_attempt_counter(self, base_user):
        issue_code(EmailVerification, base_user)
        verification = EmailVerification.objects.get(user=base_user)
        for _ in range(MAX_ATTEMPTS):
            verification.register_failure()

        issue_code(EmailVerification, base_user)
        reissued = EmailVerification.objects.get(user=base_user)

        assert reissued.attempts == 0
        assert reissued.is_valid is True

    def test_reissuing_extends_the_expiry(self, base_user):
        issue_code(EmailVerification, base_user)
        EmailVerification.objects.filter(user=base_user).update(expires_at=timezone.now() - timedelta(minutes=1))

        issue_code(EmailVerification, base_user)

        assert EmailVerification.objects.get(user=base_user).is_expired is False

    def test_the_two_models_do_not_share_a_row(self, base_user):
        verification = issue_code(EmailVerification, base_user)
        reset = issue_code(PasswordReset, base_user)

        assert EmailVerification.objects.get(user=base_user).check_code(verification) is True
        assert PasswordReset.objects.get(user=base_user).check_code(reset) is True

    def test_successive_codes_are_not_identical(self, base_user):
        """Not a uniqueness proof -- a signal that the generator is not returning a constant."""
        codes = {issue_code(EmailVerification, base_user) for _ in range(10)}

        assert len(codes) > 1
