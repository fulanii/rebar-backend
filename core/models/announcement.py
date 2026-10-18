"""The site-wide announcement banner. See docs/endpoints.md."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class Announcement(models.Model):
    """
    The banner shown across the site. A singleton: at most one row ever exists.

    `save()` pins the primary key, so every write lands on the same row, and the
    database refuses any other id, so nothing that bypasses `save()` can add a second.
    """

    SINGLETON_ID = 1

    message = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="announcements_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="announcement_is_a_singleton"),
            models.CheckConstraint(
                condition=Q(is_active=False) | ~Q(message=""),
                name="active_announcement_has_a_message",
            ),
        ]

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        """The banner, or None when none has been written."""
        return cls.objects.filter(pk=cls.SINGLETON_ID).first()

    def __str__(self):
        return f"{self.message[:40]} ({'active' if self.is_active else 'hidden'})"
