"""Start Google sign-in."""

import secrets

from django.core.cache import cache
from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from authentication.throttles import GoogleAuthRateThrottle
from authentication.utils import build_authorize_url

from .shared import STATE_CACHE_PREFIX, STATE_TTL_SECONDS, BrowserOAuthErrorMixin, callback_uri


@extend_schema(
    tags=["Authentication-Google"],
    summary="Start Google sign-in",
    responses={302: None},
)
class GoogleOAuthLoginView(BrowserOAuthErrorMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [GoogleAuthRateThrottle]

    def get(self, request):
        """
        Redirect the browser to Google's consent screen.

        **Endpoint:** GET `auth/google/login/`

        **Authentication:** None required

        **Throttle:** 20/hour per IP (`google_auth` scope)

        Point a link or `window.location` at this URL, do not fetch() it. It is a
        navigation, and the browser must actually travel to Google.

        Takes **no body, no path parameters and no query parameters**. The `state` value
        that comes back to `auth/google/callback/` is generated here, not supplied.

        ---

        ## Responses

        ### 302 Found
        Redirects to `accounts.google.com` with our client id, the callback URL, and
        a random `state` value that is also stored server-side for 10 minutes.

        The `state` is the CSRF defence: the callback accepts only a value we issued
        and have not yet consumed, so an attacker cannot walk a victim through a login
        the attacker started.

        ### 429 Too Many Requests
        Redirects to `FRONTEND_URL/login?error=google_rate_limit` rather than
        returning JSON, because this is a browser navigation.

        `/login` is a **string literal** in `shared.py`, not a setting, your frontend
        must serve that route. See `GoogleOAuthCallbackView` for the full list of
        frontend paths this flow depends on.
        """

        state = secrets.token_urlsafe(32)
        cache.set(f"{STATE_CACHE_PREFIX}{state}", "1", STATE_TTL_SECONDS)
        return HttpResponseRedirect(build_authorize_url(callback_uri(request), state))
