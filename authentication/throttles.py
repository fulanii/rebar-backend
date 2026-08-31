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


class GoogleCallbackRateThrottle(AnonRateThrottle):
    scope = "google_callback"


class CodeRequestRateThrottle(AnonRateThrottle):
    scope = "code_request"


class CodeSubmitRateThrottle(AnonRateThrottle):
    scope = "code_submit"


class PasswordResetRateThrottle(AnonRateThrottle):
    scope = "password_reset"


class ProfileUpdateRateThrottle(UserRateThrottle):
    scope = "profile_update"


class EmailChangeRateThrottle(UserRateThrottle):
    scope = "email_change"


class AccountDeletionRateThrottle(UserRateThrottle):
    scope = "account_deletion"


class UserInfoRateThrottle(UserRateThrottle):
    scope = "user_info"
