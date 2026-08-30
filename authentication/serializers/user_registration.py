"""Registration request and response shapes."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import serializers

from authentication.models import CustomUser

from .validators import validate_name, validate_password_strength, validate_us_phone_number

User = get_user_model()


class UserRegistrationRequestSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        error_messages={
            "min_length": "Password must be at least 8 characters.",
            "max_length": "Password must not exceed 128 characters.",
            "required": "Password is required.",
            "blank": "Password cannot be blank.",
        },
    )
    confirm_password = serializers.CharField(
        write_only=True,
        error_messages={
            "required": "Password confirmation is required.",
            "blank": "Password confirmation cannot be blank.",
        },
    )
    phone_number = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "Phone number is required.",
            "blank": "Phone number cannot be blank.",
        },
    )

    class Meta:
        model = CustomUser
        fields = ["email", "first_name", "last_name", "phone_number", "password", "confirm_password"]

    def validate_email(self, value):
        email = value.strip().lower()

        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")

        return email

    def validate_first_name(self, value):
        return validate_name(value, "First name")

    def validate_last_name(self, value):
        return validate_name(value, "Last name")

    def validate_phone_number(self, value):
        return validate_us_phone_number(value)

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        attrs.pop("confirm_password")
        return attrs

    def create(self, validated_data):
        try:
            return User.objects.create_user(**validated_data)
        except IntegrityError:
            raise serializers.ValidationError({"email": "An account with this email already exists."})


class UserRegistrationResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    email = serializers.EmailField()
