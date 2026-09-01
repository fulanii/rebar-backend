"""Ending every session a user has."""

from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def revoke_sessions(user):
    """
    Sign `user` out everywhere, and return how many refresh tokens were blacklisted.

    Two halves, because the two token types are stored differently. Refresh tokens are
    rows, so they are blacklisted. Access tokens are stored nowhere at all, so instead
    the account is stamped with the moment of revocation and `authentication/auth.py`
    refuses any token issued before it.

    A password reset usually means someone else is in the account, so it calls this.
    Password *change* deliberately does not, that person is signed in and gave the
    current password, so the other sessions are theirs.
    """
    outstanding = OutstandingToken.objects.filter(user=user).exclude(blacklistedtoken__isnull=False)

    blacklisted = [BlacklistedToken(token=token) for token in outstanding]
    BlacklistedToken.objects.bulk_create(blacklisted, ignore_conflicts=True)

    user.sessions_revoked_at = timezone.now()
    user.save(update_fields=["sessions_revoked_at"])

    return len(blacklisted)
