"""The profile endpoint."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestUserInfo:
    def test_returns_the_signed_in_user(self, auth_client, base_user):
        response = auth_client.get(reverse("me"))

        assert response.status_code == 200
        assert response.data["email"] == base_user.email

    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse("me"))

        assert response.status_code == 401

    @pytest.mark.parametrize("field", ["password"])
    def test_sensitive_fields_are_never_exposed(self, auth_client, field):
        response = auth_client.get(reverse("me"))

        assert field not in response.data

    def test_is_read_only(self, auth_client):
        response = auth_client.patch(reverse("me"), {"first_name": "Changed"}, format="json")

        assert response.status_code == 405
