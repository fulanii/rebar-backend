"""The user model and its manager."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestCreateUser:
    def test_password_is_hashed(self, base_user, user_password):
        assert base_user.password != user_password
        assert base_user.check_password(user_password) is True

    def test_email_is_the_username_field(self):
        assert User.USERNAME_FIELD == "email"
        assert not hasattr(User(), "username") or User().username is None

    def test_email_is_required(self):
        with pytest.raises(ValueError, match="email field must be set"):
            User.objects.create_user(email="", password="x", first_name="A", last_name="B")

    def test_first_name_is_required(self):
        with pytest.raises(ValueError, match="first name"):
            User.objects.create_user(email="a@example.com", password="x", last_name="B")

    def test_last_name_is_required(self):
        with pytest.raises(ValueError, match="last name"):
            User.objects.create_user(email="a@example.com", password="x", first_name="A")

    def test_new_users_default_to_inactive_and_unverified(self, db):
        user = User.objects.create_user(email="fresh@example.com", password="x", first_name="A", last_name="B")

        assert user.is_active is False
        assert user.is_verified is False
        assert user.is_suspended is False

    def test_absent_phone_number_is_empty_string_not_none(self, db):
        user = User.objects.create_user(email="nophone@example.com", password="x", first_name="A", last_name="B")

        assert user.phone_number == ""


class TestCreateSuperuser:
    def test_superuser_is_staff_and_active(self, db):
        admin = User.objects.create_superuser(email="admin@example.com", password="x", first_name="Ad", last_name="Min")

        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_active is True
        assert admin.is_verified is True
