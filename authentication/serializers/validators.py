"""Field validators shared across serializers."""

import re

import phonenumbers
from rest_framework import serializers

NAME_EXTRA_CHARS = {" ", "-", "'", "’"}

SPECIAL_CHARS = r"[!@#$%^&*(),.?\":{}|<>\-_+=\[\]~/`';\\]"


def validate_name(value, field_label):
    """A person's name: at least two characters, letters plus spaces, hyphens and apostrophes."""
    name = value.strip()

    if len(name) < 2:
        raise serializers.ValidationError(f"{field_label} must be at least 2 characters.")

    if not all(char.isalpha() or char in NAME_EXTRA_CHARS for char in name):
        raise serializers.ValidationError(f"{field_label} can only contain letters, spaces, hyphens, and apostrophes.")

    return name


def validate_phone_number(value):
    """Any country's number, typed with `+` and its country code, normalized to E.164: `+12015550123`."""
    if not value.strip().startswith("+"):
        raise serializers.ValidationError("Start with + and the country code, e.g. +1 201 555 0123.")

    try:
        number = phonenumbers.parse(value)
    except phonenumbers.NumberParseException:
        number = None

    if number is None or not phonenumbers.is_valid_number(number):
        raise serializers.ValidationError("Enter a valid phone number, e.g. +1 201 555 0123.")

    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def validate_password_strength(value):
    """Require an uppercase letter, a lowercase letter, a digit and a special character."""
    errors = []

    if not re.search(r"[A-Z]", value):
        errors.append("Password must contain at least one uppercase letter.")

    if not re.search(r"[a-z]", value):
        errors.append("Password must contain at least one lowercase letter.")

    if not re.search(r"\d", value):
        errors.append("Password must contain at least one digit.")

    if not re.search(SPECIAL_CHARS, value):
        errors.append("Password must contain at least one special character.")

    if errors:
        raise serializers.ValidationError(errors)

    return value


def validate_verification_code(value):
    """A code is exactly six digits, as a string."""
    code = value.strip()

    if not (len(code) == 6 and code.isdigit()):
        raise serializers.ValidationError("Enter the 6-digit code from your email.")

    return code
