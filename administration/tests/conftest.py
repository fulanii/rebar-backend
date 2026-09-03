"""Fixtures for the administration app. See docs/ai/conventions.md."""

from datetime import timedelta

import pytest
from django.utils import timezone

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
def admin_client(api_client, staff_user):
    """
    A client authenticated as `staff_user`.

    Skips token validation, so tests *about* authentication send a real token instead.
    """
    api_client.force_authenticate(user=staff_user)
    return api_client


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
