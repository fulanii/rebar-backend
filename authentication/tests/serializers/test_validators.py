"""The shared field validators."""

import pytest
from rest_framework import serializers

from authentication.serializers.validators import (
    validate_name,
    validate_password_strength,
    validate_phone_number,
    validate_verification_code,
)


class TestPhoneNumber:
    @pytest.mark.parametrize(
        "raw",
        [
            "+12015550123",
            "+1 201 555 0123",
            "+1 (201) 555-0123",
            "+1.201.555.0123",
            "  +1 201 555 0123  ",
        ],
    )
    def test_every_format_normalizes_to_e164(self, raw):
        assert validate_phone_number(raw) == "+12015550123"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("+33 6 12 34 56 78", "+33612345678"),
            ("+227 90 12 34 56", "+22790123456"),
            ("+49 1512 3456789", "+4915123456789"),
            ("+81 90-1234-5678", "+819012345678"),
        ],
    )
    def test_a_number_from_any_country_is_accepted(self, raw, expected):
        assert validate_phone_number(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "2015550123",
            "(201) 555-0123",
            "1-201-555-0123",
            "06 12 34 56 78",
            "001 201 555 0123",
        ],
    )
    def test_a_number_without_its_country_code_is_rejected(self, raw):
        """Its country is a guess, and a guess stores somebody else's number."""
        with pytest.raises(serializers.ValidationError, match="Start with \\+"):
            validate_phone_number(raw)

    @pytest.mark.parametrize(
        "raw",
        [
            "+1 201 555 012",
            "+1 201 555 01234",
            "+",
            "+abcdefghij",
            "+999 123 456 789",
        ],
    )
    def test_a_number_that_is_not_valid_is_rejected(self, raw):
        with pytest.raises(serializers.ValidationError, match="valid phone number"):
            validate_phone_number(raw)

    def test_a_number_that_cannot_exist_is_rejected(self):
        """The right length is not enough: 555 is not a real US area code."""
        with pytest.raises(serializers.ValidationError):
            validate_phone_number("+1 555 123 4567")

    def test_an_empty_number_is_rejected(self):
        with pytest.raises(serializers.ValidationError):
            validate_phone_number("")


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
