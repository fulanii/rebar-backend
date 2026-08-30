"""The shared field validators."""

import pytest
from rest_framework import serializers

from authentication.serializers.validators import (
    validate_name,
    validate_password_strength,
    validate_us_phone_number,
    validate_verification_code,
)


class TestPhoneNumber:
    @pytest.mark.parametrize(
        "raw",
        [
            "5551234567",
            "555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "+1 555 123 4567",
            "1-555-123-4567",
            "  555 123 4567  ",
        ],
    )
    def test_every_format_normalizes_to_ten_digits(self, raw):
        assert validate_us_phone_number(raw) == "5551234567"

    @pytest.mark.parametrize(
        "raw",
        [
            "555123456",
            "55512345678",
            "",
            "abcdefghij",
        ],
    )
    def test_wrong_length_is_rejected(self, raw):
        with pytest.raises(serializers.ValidationError):
            validate_us_phone_number(raw)

    @pytest.mark.parametrize("raw", ["0551234567", "1551234567"])
    def test_area_code_cannot_start_with_zero_or_one(self, raw):
        with pytest.raises(serializers.ValidationError):
            validate_us_phone_number(raw)


class TestName:
    @pytest.mark.parametrize("raw", ["Jane", "Anne-Marie", "O'Brien", "van der Berg", "Zoë", "Müller", "田中"])
    def test_real_names_are_accepted(self, raw):
        assert validate_name(raw, "First name") == raw

    def test_whitespace_is_trimmed(self):
        assert validate_name("  Jane  ", "First name") == "Jane"

    @pytest.mark.parametrize("raw", ["J", "", "  "])
    def test_too_short_is_rejected(self, raw):
        with pytest.raises(serializers.ValidationError):
            validate_name(raw, "First name")

    @pytest.mark.parametrize("raw", ["Jane123", "Jane@Doe", "<script>"])
    def test_digits_and_symbols_are_rejected(self, raw):
        with pytest.raises(serializers.ValidationError):
            validate_name(raw, "First name")


class TestPasswordStrength:
    def test_a_strong_password_passes(self):
        assert validate_password_strength("SecurePass123!") == "SecurePass123!"

    @pytest.mark.parametrize(
        "raw,missing",
        [
            ("securepass123!", "uppercase"),
            ("SECUREPASS123!", "lowercase"),
            ("SecurePassword!", "digit"),
            ("SecurePass1234", "special"),
        ],
    )
    def test_each_missing_character_class_is_reported(self, raw, missing):
        with pytest.raises(serializers.ValidationError) as exc:
            validate_password_strength(raw)

        assert missing in str(exc.value).lower()

    def test_all_failures_are_reported_at_once(self):
        with pytest.raises(serializers.ValidationError) as exc:
            validate_password_strength("aaaaaaaa")

        assert len(exc.value.detail) == 3


class TestVerificationCode:
    def test_a_six_digit_string_passes(self):
        assert validate_verification_code("004821") == "004821"

    @pytest.mark.parametrize("raw", ["12345", "1234567", "12345a", "", "abcdef"])
    def test_anything_else_is_rejected(self, raw):
        with pytest.raises(serializers.ValidationError):
            validate_verification_code(raw)
