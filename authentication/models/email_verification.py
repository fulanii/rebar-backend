"""The code that proves a user owns the email address they signed up with."""

from .one_time_code import OneTimeCode


class EmailVerification(OneTimeCode):
    class Meta(OneTimeCode.Meta):
        abstract = False

    def __str__(self):
        return f"Email verification code for {self.user.email}"
