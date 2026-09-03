"""View exports. Import from the package, not from the module files."""

from .account_update import (
    AccountDeletionView,
    EmailChangeConfirmView,
    EmailChangeRequestView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileUpdateView,
)
from .google_auth import GoogleOAuthCallbackView, GoogleOAuthExchangeView, GoogleOAuthLoginView
from .jwt_tokens import CustomTokenBlacklistView, CustomTokenRefreshView
from .user_info import UserInfoView
from .user_login import UserLoginView
from .user_registration import UserRegistrationView
from .verifications import EmailVerificationResendView, EmailVerificationView

__all__ = [
    "AccountDeletionView",
    "EmailChangeRequestView",
    "EmailChangeConfirmView",
    "EmailVerificationView",
    "EmailVerificationResendView",
    "GoogleOAuthLoginView",
    "GoogleOAuthCallbackView",
    "GoogleOAuthExchangeView",
    "CustomTokenRefreshView",
    "CustomTokenBlacklistView",
    "PasswordResetRequestView",
    "PasswordResetConfirmView",
    "PasswordChangeView",
    "ProfileUpdateView",
    "UserInfoView",
    "UserLoginView",
    "UserRegistrationView",
]
