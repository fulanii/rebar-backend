"""The account shape returned for one user, for support and operations."""

from rest_framework import serializers

from authentication.models import CustomUser


class UserDetailResponseSerializer(serializers.ModelSerializer):
    """
    One account in full. Read-only, and never a credential or a code.

    Carries `sessions_revoked_at`, which the list deliberately leaves out. Support asks
    "was this account signed out, and when" about one person, never about a page of
    them, and the answer is a timestamp rather than anything that grants access.
    """

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
            "is_staff",
            "is_superuser",
            "auth_provider",
            "date_joined",
            "last_login",
            "sessions_revoked_at",
        ]
        read_only_fields = fields
