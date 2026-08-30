"""Field validators shared across serializers."""

import re

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


def validate_us_phone_number(value):
    """Normalize a US phone number to exactly ten digits."""
    digits = re.sub(r"\D", "", value)

    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        raise serializers.ValidationError("Enter a valid 10-digit US phone number.")

    if digits[0] in ("0", "1"):
        raise serializers.ValidationError("Invalid US area code. Area codes cannot start with 0 or 1.")

    return digits


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
