"""Submitting the emailed verification code."""

from rest_framework import serializers

from authentication.serializers.validators import validate_verification_code


class EmailVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()

    def validate_email(self, value):
        return value.strip().lower()

    def validate_code(self, value):
        return validate_verification_code(value)
