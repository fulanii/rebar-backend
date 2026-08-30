"""View exports. Import from the package, not from the module files."""

from .google_auth import GoogleOAuthCallbackView, GoogleOAuthExchangeView, GoogleOAuthLoginView
from .jwt_tokens import CustomTokenBlacklistView, CustomTokenObtainPairView, CustomTokenRefreshView
from .passwords import PasswordChangeView, PasswordResetConfirmView, PasswordResetRequestView
from .user_info import UserInfoView
from .user_login import UserLoginView
from .user_registration import UserRegistrationView
from .verifications import EmailVerificationResendView, EmailVerificationView

__all__ = [
    "EmailVerificationView",
    "EmailVerificationResendView",
    "GoogleOAuthLoginView",
    "GoogleOAuthCallbackView",
    "GoogleOAuthExchangeView",
    "CustomTokenObtainPairView",
    "CustomTokenRefreshView",
    "CustomTokenBlacklistView",
    "PasswordResetRequestView",
    "PasswordResetConfirmView",
    "PasswordChangeView",
    "UserInfoView",
    "UserLoginView",
    "UserRegistrationView",
]
