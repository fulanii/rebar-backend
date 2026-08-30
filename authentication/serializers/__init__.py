"""Serializer exports. Import from the package, not from the module files."""

from .common import DetailResponseSerializer
from .google_auth import GoogleOAuthExchangeRequestSerializer, GoogleOAuthExchangeResponseSerializer
from .jwt_tokens import TokenObtainPairResponseSerializer, TokenRefreshResponseSerializer
from .passwords import PasswordChangeSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer
from .user_info import UserInfoSerializer
from .user_login import UserLoginRequestSerializer, UserLoginResponseSerializer
from .user_registration import UserRegistrationRequestSerializer, UserRegistrationResponseSerializer
from .verifications import EmailVerificationRequestSerializer, ResendVerificationRequestSerializer

__all__ = [
    "DetailResponseSerializer",
    "EmailVerificationRequestSerializer",
    "ResendVerificationRequestSerializer",
    "GoogleOAuthExchangeRequestSerializer",
    "GoogleOAuthExchangeResponseSerializer",
    "TokenObtainPairResponseSerializer",
    "TokenRefreshResponseSerializer",
    "PasswordChangeSerializer",
    "PasswordResetConfirmSerializer",
    "PasswordResetRequestSerializer",
    "UserInfoSerializer",
    "UserLoginRequestSerializer",
    "UserLoginResponseSerializer",
    "UserRegistrationRequestSerializer",
    "UserRegistrationResponseSerializer",
]
