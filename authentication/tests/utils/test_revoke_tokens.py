"""Ending every session a user has."""

import pytest
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.utils import revoke_sessions

pytestmark = pytest.mark.django_db


def blacklisted(user):
    return BlacklistedToken.objects.filter(token__user=user).count()


class TestRevokeSessions:
    def test_revokes_every_outstanding_token(self, base_user):
        for _ in range(3):
            RefreshToken.for_user(base_user)

        assert revoke_sessions(base_user) == 3
        assert blacklisted(base_user) == 3

    def test_a_revoked_token_no_longer_verifies(self, base_user):
        refresh = RefreshToken.for_user(base_user)
        revoke_sessions(base_user)

        with pytest.raises(TokenError):
            RefreshToken(str(refresh)).check_blacklist()

    def test_leaves_other_users_alone(self, base_user, second_user):
        RefreshToken.for_user(base_user)
        RefreshToken.for_user(second_user)

        revoke_sessions(base_user)

        assert blacklisted(base_user) == 1
        assert blacklisted(second_user) == 0

    def test_is_a_no_op_without_tokens(self, base_user):
        assert revoke_sessions(base_user) == 0

    def test_running_twice_does_not_duplicate(self, base_user):
        RefreshToken.for_user(base_user)

        revoke_sessions(base_user)
        assert revoke_sessions(base_user) == 0
        assert blacklisted(base_user) == 1
        assert OutstandingToken.objects.filter(user=base_user).count() == 1

    def test_stamps_the_account(self, base_user):
        revoke_sessions(base_user)
        base_user.refresh_from_db()

        assert base_user.sessions_revoked_at is not None

    def test_stamps_an_account_with_no_tokens(self, base_user):
        assert revoke_sessions(base_user) == 0

        base_user.refresh_from_db()
        assert base_user.sessions_revoked_at is not None
