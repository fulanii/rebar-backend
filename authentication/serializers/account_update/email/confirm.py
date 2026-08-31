"""Confirming an email change with the code sent to the new address."""

from rest_framework import serializers

from ...validators import validate_verification_code


class EmailChangeConfirmSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate_code(self, value):
        return validate_verification_code(value)


class EmailChangeConfirmResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    email = serializers.EmailField()
