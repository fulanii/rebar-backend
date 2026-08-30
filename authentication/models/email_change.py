"""The code that proves a user owns the address they want to move their account to."""

from django.db import models

from .one_time_code import OneTimeCode


class EmailChange(OneTimeCode):
    new_email = models.EmailField()

    class Meta(OneTimeCode.Meta):
        abstract = False

    def __str__(self):
        return f"Email change code for {self.user.email} -> {self.new_email}"
