"""The admin user list: which accounts to return, and the shape of each one."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers
from rest_framework.fields import empty

from authentication.models import CustomUser

USER_LIST_ORDERING_FIELDS = ("date_joined", "last_login", "email", "first_name", "last_name")

DEFAULT_USER_LIST_ORDERING = "-date_joined"


class OptionalBooleanField(serializers.BooleanField):
    """
    A boolean query parameter that is left out when it was not sent.

    DRF reads a missing boolean in query params as `False`, so without this an
    unfiltered list would quietly become a list of inactive, unsuspended non-staff.
    """

    default_empty_html = empty


class UserListQueryRequestSerializer(serializers.Serializer):
    """
    The list's query parameters. Only the filters actually sent appear in the result.

    `timezone` comes back as a `ZoneInfo`, defaulting to UTC, and decides which day
    the `joined_*` bounds mean.
    """

    search = serializers.CharField(required=False, allow_blank=True, max_length=254)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=32)
    has_phone = OptionalBooleanField(required=False)
    is_active = OptionalBooleanField(required=False)
    is_verified = OptionalBooleanField(required=False)
    is_phone_verified = OptionalBooleanField(required=False)
    is_suspended = OptionalBooleanField(required=False)
    is_staff = OptionalBooleanField(required=False)
    has_logged_in = OptionalBooleanField(required=False)
    auth_provider = serializers.ChoiceField(choices=CustomUser.AuthProvider.choices, required=False)
    joined_after = serializers.DateField(required=False)
    joined_before = serializers.DateField(required=False)
    timezone = serializers.CharField(required=False, default="UTC")
    ordering = serializers.ChoiceField(
        choices=[prefix + field for field in USER_LIST_ORDERING_FIELDS for prefix in ("", "-")],
        required=False,
        default=DEFAULT_USER_LIST_ORDERING,
    )

    def validate_phone(self, value):
        digits = "".join(char for char in value if char.isdigit())

        if value and not digits:
            raise serializers.ValidationError("Must contain at least one digit.")

        return digits

    def validate_timezone(self, value):
        try:
            return ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError(f'"{value}" is not a known time zone, e.g. "Europe/Paris".')

    def validate(self, attrs):
        after, before = attrs.get("joined_after"), attrs.get("joined_before")

        if after and before and after > before:
            raise serializers.ValidationError({"joined_before": ["Must be on or after joined_after."]})

        return attrs


class UserListQueryResponseSerializer(serializers.ModelSerializer):
    """One row of the admin list. Read-only, and never a credential or a code."""

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
            "is_phone_verified",
            "is_suspended",
            "auth_provider",
            "date_joined",
            "last_login",
            "is_staff",
            "is_superuser",
        ]
        read_only_fields = fields
