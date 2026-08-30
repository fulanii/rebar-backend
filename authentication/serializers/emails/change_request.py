"""Asking to move an account to a new email address."""

from rest_framework import serializers

from authentication.models import CustomUser


class EmailChangeRequestSerializer(serializers.Serializer):
    new_email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_new_email(self, value):
        email = value.strip().lower()
        user = self.context["request"].user

        if email == user.email:
            raise serializers.ValidationError("This is already your email address.")

        if CustomUser.objects.filter(email=email, is_verified=True).exists():
            raise serializers.ValidationError("This email address is not available.")

        return email

    def validate_password(self, value):
        user = self.context["request"].user

        if not user.has_usable_password():
            raise serializers.ValidationError("This account signs in with Google and has no password.")

        if not user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.")

        return value
