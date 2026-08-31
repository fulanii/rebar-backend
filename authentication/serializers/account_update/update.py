"""Editing the name on your own account."""

from rest_framework import serializers

from authentication.models import CustomUser

from ..validators import validate_name


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Only the fields a person may change about themselves without proving anything."""

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name"]

    def validate_first_name(self, value):
        return validate_name(value, "First name")

    def validate_last_name(self, value):
        return validate_name(value, "Last name")

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Send at least one field to change.")

        return attrs
