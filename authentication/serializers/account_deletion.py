"""Confirming that a user really means to delete their account."""

from rest_framework import serializers


class AccountDeletionSerializer(serializers.Serializer):
    """Typing the address guards against a misfire; the password guards against a stolen token."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate_email(self, value):
        user = self.context["request"].user

        if value.strip().lower() != user.email:
            raise serializers.ValidationError("This does not match the email address on your account.")

        return value

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.has_usable_password():
            return attrs

        if not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})

        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError({"password": "Password is incorrect."})

        return attrs
