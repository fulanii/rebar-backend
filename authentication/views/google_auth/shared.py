"""Constants and helpers shared by the three Google sign-in views."""

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework.exceptions import Throttled

STATE_TTL_SECONDS = 600

EXCHANGE_TTL_SECONDS = 120

STATE_CACHE_PREFIX = "google_oauth_state:"

EXCHANGE_CACHE_PREFIX = "google_oauth_exchange:"


def callback_uri(request):
    """Must match a redirect URI registered on the Google OAuth client exactly."""
    return request.build_absolute_uri(reverse("google-oauth-callback"))


def frontend_redirect(path):
    return HttpResponseRedirect(f"{settings.FRONTEND_URL.rstrip('/')}{path}")


class BrowserOAuthErrorMixin:
    """Redirects errors to the frontend, for endpoints reached by browser navigation."""

    def handle_exception(self, exc):
        if isinstance(exc, Throttled):
            return frontend_redirect("/login?error=google_rate_limit")
        return super().handle_exception(exc)
