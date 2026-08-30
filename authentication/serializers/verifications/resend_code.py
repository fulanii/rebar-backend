"""Asking for a fresh verification code."""

from rest_framework import serializers


class ResendVerificationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()
