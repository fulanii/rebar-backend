"""Rate limits, one class per endpoint. Rates live in settings.DEFAULT_THROTTLE_RATES."""

from rest_framework.throttling import AnonRateThrottle


class AnnouncementRateThrottle(AnonRateThrottle):
    """`120/minute` per IP, read on every page load, signed in or not."""

    scope = "core_announcement"
