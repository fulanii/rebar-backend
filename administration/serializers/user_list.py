"""The account shape returned by the admin user list."""

from rest_framework import serializers

from authentication.models import CustomUser


class UserListResponseSerializer(serializers.ModelSerializer):
    """One row of the admin list. Read-only, and never a credential or a code."""

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_active",
            "is_verified",
            "is_suspended",
            "auth_provider",
            "date_joined",
            "last_login",
            "is_staff",
            "is_superuser",
        ]
        read_only_fields = fields
