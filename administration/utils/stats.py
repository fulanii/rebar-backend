"""The figures on the admin overview. Billing adds its own here when it lands."""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from authentication.models import CustomUser

RECENT = timedelta(days=7)


def account_stats():
    """Every account, and the ones created in the last seven days, rolling, in one query."""
    return CustomUser.objects.aggregate(
        total_users=Count("id"),
        signups_last_7_days=Count("id", filter=Q(date_joined__gte=timezone.now() - RECENT)),
    )
