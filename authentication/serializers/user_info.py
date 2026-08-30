"""The user profile shape, returned by every endpoint that identifies someone."""

from rest_framework import serializers

from authentication.models import CustomUser


class UserInfoSerializer(serializers.ModelSerializer):
    """Only fields a user may see about themselves. Never add permission flags here."""

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_verified",
            "is_active",
            "auth_provider",
            "date_joined",
        ]
        read_only_fields = fields
