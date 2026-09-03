"""Fixtures for the administration app. See docs/ai/conventions.md."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import CustomUser


@pytest.fixture
def staff_user(db, user_password):
    """A verified, active account with the staff flag."""
    return CustomUser.objects.create_user(
        email="operator@example.com",
        password=user_password,
        first_name="Ops",
        last_name="Person",
        is_active=True,
        is_verified=True,
        is_staff=True,
    )


@pytest.fixture
def admin_client(staff_user):
    """
    A client authenticated as `staff_user`, and its own client.

    Its own, because a test that wants two operators at once would otherwise get one:
    `force_authenticate` on a shared client rebinds it, and the second fixture silently
    wins. Skips token validation, so tests *about* authentication send a real token.
    """
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def many_users(db):
    """
    Thirty accounts, each a minute older than the last.

    `bulk_create` skips password hashing, which is the whole cost of building a list
    this long, and none of these accounts ever signs in.
    """

    def make(count, prefix="user"):
        now = timezone.now()
        return CustomUser.objects.bulk_create(
            CustomUser(
                email=f"{prefix}{number}@example.com",
                first_name="Test",
                last_name=f"User{number}",
                date_joined=now - timedelta(minutes=number),
            )
            for number in range(count)
        )

    return make


@pytest.fixture
def token_client():
    """
    Builds a client carrying a genuine access token.

    `force_authenticate` bypasses the authentication class, so a test of the suspension
    gate, which lives in that class, has to send a real token instead.
    """

    def make(user):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return client

    return make


@pytest.fixture
def superuser(db, user_password):
    """A verified, active superuser: the only account the update endpoint accepts."""
    return CustomUser.objects.create_superuser(
        email="root@example.com",
        password=user_password,
        first_name="Root",
        last_name="Person",
    )


@pytest.fixture
def superuser_client(superuser):
    """A client authenticated as `superuser`, on its own client for the same reason."""
    client = APIClient()
    client.force_authenticate(user=superuser)
    return client
