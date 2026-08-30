"""The code that authorizes a password reset."""

from .one_time_code import OneTimeCode


class PasswordReset(OneTimeCode):
    class Meta(OneTimeCode.Meta):
        abstract = False

    def __str__(self):
        return f"Password reset code for {self.user.email}"
