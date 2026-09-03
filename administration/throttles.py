"""Rate limits, one class per endpoint. Rates live in settings.DEFAULT_THROTTLE_RATES."""

from rest_framework.throttling import UserRateThrottle


class AdminReadRateThrottle(UserRateThrottle):
    """`120/minute`, read-only, an operator paging through a list."""

    scope = "admin_read"


class AdminWriteRateThrottle(UserRateThrottle):
    """`60/minute`, writes. Support edits one account at a time, a script does not."""

    scope = "admin_write"
