"""Rate limits, one class per endpoint. Rates live in settings.DEFAULT_THROTTLE_RATES."""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class RegistrationRateThrottle(AnonRateThrottle):
    scope = "registration"


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class TokenRefreshRateThrottle(AnonRateThrottle):
    scope = "token_refresh"


class GoogleAuthRateThrottle(AnonRateThrottle):
    scope = "google_auth"


class CodeRequestRateThrottle(AnonRateThrottle):
    scope = "code_request"


class CodeSubmitRateThrottle(AnonRateThrottle):
    scope = "code_submit"


class PasswordResetRateThrottle(AnonRateThrottle):
    scope = "password_reset"


class UserInfoRateThrottle(UserRateThrottle):
    scope = "user_info"
