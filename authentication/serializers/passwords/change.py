"""Changing a password while signed in."""

from rest_framework import serializers

from ..validators import validate_password_strength


class PasswordChangeSerializer(serializers.Serializer):
    """The current password is required even though the request is authenticated."""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")

        return value

    def validate_new_password(self, value):
        return validate_password_strength(value)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError({"new_password": "New password must be different from the current one."})

        attrs.pop("confirm_password")
        return attrs
