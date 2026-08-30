"""Shared base for the 6-digit codes emailed for verification and password reset."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

CODE_LIFETIME = timedelta(minutes=15)
MAX_ATTEMPTS = 5


def default_expiry():
    return timezone.now() + CODE_LIFETIME


class OneTimeCode(models.Model):
    """A hashed, expiring, single-use code belonging to one user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)s",
    )
    code = models.CharField(max_length=128)
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def set_code(self, raw_code):
        self.code = make_password(raw_code)

    def check_code(self, raw_code):
        return check_password(raw_code, self.code)

    def mark_used(self):
        self.used = True
        self.used_at = timezone.now()
        self.save(update_fields=["used", "used_at"])

    def register_failure(self):
        """
        Count a wrong guess, and burn the code once MAX_ATTEMPTS is reached.

        The per-IP throttle does not stop the same code being guessed from many
        addresses at once; this does. Returns True if the code was burned.
        """
        self.attempts += 1
        exhausted = self.attempts >= MAX_ATTEMPTS

        if exhausted:
            self.used = True
            self.used_at = timezone.now()

        self.save(update_fields=["attempts", "used", "used_at"])
        return exhausted

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_exhausted(self):
        return self.attempts >= MAX_ATTEMPTS

    @property
    def is_valid(self):
        return not self.used and self.used_at is None and not self.is_expired and not self.is_exhausted
