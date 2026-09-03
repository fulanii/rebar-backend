"""Rate limits, one class per endpoint. Rates live in settings.DEFAULT_THROTTLE_RATES."""

from rest_framework.throttling import UserRateThrottle


class AdminReadRateThrottle(UserRateThrottle):
    """`120/minute`, read-only, an operator paging through a list."""

    scope = "admin_read"
