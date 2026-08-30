"""Issuing a fresh one-time code to a user."""

from authentication.models.one_time_code import default_expiry

from .generate_code import generate_6_digit_code


def issue_code(model, user):
    """
    Generate a new code for `user`, store its hash, and return the raw digits.

    `update_or_create` keeps one live code per user, so issuing a new one replaces
    the old and the previous code stops working immediately.
    """
    raw_code = generate_6_digit_code()

    hashed = model(user=user)
    hashed.set_code(raw_code)

    model.objects.update_or_create(
        user=user,
        defaults={
            "code": hashed.code,
            "used": False,
            "used_at": None,
            "attempts": 0,
            "expires_at": default_expiry(),
        },
    )

    return raw_code
