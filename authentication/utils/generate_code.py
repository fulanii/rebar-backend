"""Generation of the 6-digit codes we email."""

import secrets


def generate_6_digit_code():
    """A cryptographically strong, zero-padded 6-digit string, e.g. `"004821"`."""
    return f"{secrets.randbelow(1_000_000):06d}"
