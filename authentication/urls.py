"""
Authentication routes, mounted at `/auth/` in config/urls.py.

The JWT token endpoints are NOT here -- they live at `/token/` in the root URLconf,
because the refresh cookie is scoped to that path.
"""

from django.urls import path

from authentication.views import (
    EmailVerificationResendView,
    EmailVerificationView,
    GoogleOAuthCallbackView,
    GoogleOAuthExchangeView,
    GoogleOAuthLoginView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserInfoView,
    UserLoginView,
    UserRegistrationView,
)

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify-email"),
    path("resend-verification/", EmailVerificationResendView.as_view(), name="resend-verification"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("me/", UserInfoView.as_view(), name="me"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("change-password/", PasswordChangeView.as_view(), name="change-password"),
    path("google/login/", GoogleOAuthLoginView.as_view(), name="google-oauth-login"),
    path("google/callback/", GoogleOAuthCallbackView.as_view(), name="google-oauth-callback"),
    path("google/exchange/", GoogleOAuthExchangeView.as_view(), name="google-oauth-exchange"),
]
