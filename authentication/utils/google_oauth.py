"""
Helpers for the server-side Google OAuth flow.

The sequence and the reasoning behind it are in docs/ai/architecture.md.
"""

from urllib.parse import urlencode

import requests
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import CustomUser

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = "openid email profile"


def build_authorize_url(redirect_uri, state):
    """The Google consent-screen URL to send the browser to."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code, redirect_uri):
    """
    Trade the authorization `code` for Google's token set, which carries the `id_token`.

    `redirect_uri` must be identical to the one used to obtain the code.
    Raises `requests.RequestException` on any HTTP or network error.
    """
    response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_or_create_google_user(email, first_name, last_name):
    """
    Resolve the account for a Google identity, creating it on first sign-in.

    Returns `(user, created)`. Google has already verified the address, so these
    accounts skip our own verification and are created with an unusable password.

    Adopting an existing **unverified** row also discards its password. Nobody ever
    proved they owned that address, so nobody proved they set that password, see
    docs/ai/guardrails.md on pre-hijacking. A verified account keeps its password:
    that person did prove ownership, and Google should be a second way in, not a
    lockout.
    """
    email = email.lower().strip()
    first_name = (first_name or "").strip() or email.split("@")[0]
    last_name = (last_name or "").strip()

    user = CustomUser.objects.filter(email=email).first()

    if user is not None:
        if user.is_verified:
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])
            return user, False

        user.set_unusable_password()
        user.auth_provider = CustomUser.AuthProvider.GOOGLE
        user.is_active = True
        user.is_verified = True
        user.save(update_fields=["password", "auth_provider", "is_active", "is_verified"])
        return user, False

    user = CustomUser(
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_active=True,
        is_verified=True,
        auth_provider=CustomUser.AuthProvider.GOOGLE,
    )
    user.set_unusable_password()
    user.save()
    return user, True


def build_user_payload(user):
    """The profile block returned by every endpoint that logs someone in."""
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
        "is_verified": user.is_verified,
        "is_active": user.is_active,
        "auth_provider": user.auth_provider,
    }


def issue_jwt_payload(user):
    """
    A fresh token pair plus the user's profile.

    The caller moves `refresh` into the httpOnly cookie before responding.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user_data": build_user_payload(user),
    }
