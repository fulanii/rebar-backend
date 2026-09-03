"""One suspension of one account, and who lifted it. See docs/endpoints.md."""

from django.db import models

from authentication.models import CustomUser


class Suspension(models.Model):
    class SuspensionReason(models.TextChoices):
        SPAM = "spam", "Spam"
        FRAUD = "fraud", "Fraud"
        CHARGEBACK = "chargeback", "Chargeback"
        ABUSE = "abuse", "Abuse"
        TOS = "tos", "Terms of Service"
        MANUAL = "manual", "Manual"

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="suspensions")
    reason = models.CharField(max_length=30, choices=SuspensionReason.choices, default=SuspensionReason.MANUAL)
    notes = models.TextField(blank=True)

    suspended_at = models.DateTimeField(auto_now_add=True)
    suspended_by = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="suspensions_issued"
    )

    lifted_at = models.DateTimeField(null=True, blank=True)
    lifted_by = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="suspensions_lifted"
    )

    class Meta:
        ordering = ["-suspended_at"]
        indexes = [models.Index(fields=["user", "-suspended_at"])]

    def __str__(self):
        return f"{self.user} — {self.reason} ({self.suspended_at:%Y-%m-%d})"
