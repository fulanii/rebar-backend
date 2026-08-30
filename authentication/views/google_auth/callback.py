"""Handle Google's redirect back, then hand off to the frontend."""

import logging
import secrets

import requests
from django.conf import settings
from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from authentication.utils import exchange_code_for_tokens, get_or_create_google_user, issue_jwt_payload

from .shared import (
    EXCHANGE_CACHE_PREFIX,
    EXCHANGE_TTL_SECONDS,
    STATE_CACHE_PREFIX,
    BrowserOAuthErrorMixin,
    callback_uri,
    frontend_redirect,
)

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Google"],
    summary="Google sign-in callback",
    parameters=[
        OpenApiParameter(name="code", type=str, location=OpenApiParameter.QUERY),
        OpenApiParameter(name="state", type=str, location=OpenApiParameter.QUERY),
        OpenApiParameter(name="error", type=str, location=OpenApiParameter.QUERY),
    ],
    responses={302: None},
)
class GoogleOAuthCallbackView(BrowserOAuthErrorMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Handle Google's redirect back, then hand off to the frontend.

        **Endpoint:** GET `auth/google/callback/`

        **Authentication:** None required

        **Called by Google, not by your frontend.** Register this exact URL as an
        authorized redirect URI on the Google OAuth client.

        ---

        ## Query Parameters

        | Field | Type   | Description                                          |
        |-------|--------|------------------------------------------------------|
        | code  | string | One-time authorization code, exchanged server-side.  |
        | state | string | The value we issued at `auth/google/login/`.         |
        | error | string | Present when the user cancelled or Google refused.   |

        ---

        ## Responses

        ### 302 Found — success
        Redirects to `FRONTEND_URL/auth/callback#code=<one-time-code>`.

        The handoff code goes in the URL **fragment**, not the query string: fragments
        are never sent to a server, so it stays out of proxy and server logs. The
        frontend reads it and posts it to `auth/google/exchange/`.

        JWTs are deliberately not put in the URL at all -- they would land in browser
        history and in the `Referer` header of the next request.

        ### 302 Found — failure
        Redirects to `FRONTEND_URL/login?error=google` for every failure: the user
        cancelled, `state` was missing/forged/already used, the code exchange failed,
        or Google returned no email. The reason is logged server-side; the browser is
        told only that it did not work.

        ---

        ## Post-Request Flow
        1. Reject the request unless both `code` and `state` are present.
        2. Look up `state` and **delete it immediately** -- it is single-use, so a
           captured callback URL cannot be replayed.
        3. Exchange the code for Google's tokens (server-to-server, using the client
           secret) and cryptographically verify the returned `id_token`.
        4. Get or create the user. Google has verified the address, so the account is
           created active and verified, with an unusable password.
        5. Issue JWTs, store them under a fresh single-use handoff code for 2 minutes,
           and redirect into the frontend.
        """

        error = request.GET.get("error")
        code = request.GET.get("code")
        state = request.GET.get("state")

        if error or not code or not state:
            logger.warning("event=google_oauth_callback_bad_request error=%s", error)
            return frontend_redirect("/login?error=google")

        state_key = f"{STATE_CACHE_PREFIX}{state}"
        if cache.get(state_key) is None:
            logger.warning("event=google_oauth_invalid_state")
            return frontend_redirect("/login?error=google")
        cache.delete(state_key)

        try:
            tokens = exchange_code_for_tokens(code, callback_uri(request))
            payload = id_token.verify_oauth2_token(
                tokens["id_token"],
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
                clock_skew_in_seconds=10,
            )
        except (requests.RequestException, ValueError, KeyError):
            logger.warning("event=google_oauth_exchange_failed", exc_info=True)
            return frontend_redirect("/login?error=google")

        email = payload.get("email")
        if not email:
            logger.warning("event=google_oauth_missing_email")
            return frontend_redirect("/login?error=google")

        user, created = get_or_create_google_user(
            email,
            payload.get("given_name", ""),
            payload.get("family_name", ""),
        )
        logger.info("event=google_oauth_success email=%s new_user=%s", user.email, created)

        handoff_code = secrets.token_urlsafe(32)
        cache.set(f"{EXCHANGE_CACHE_PREFIX}{handoff_code}", issue_jwt_payload(user), EXCHANGE_TTL_SECONDS)

        return frontend_redirect(f"/auth/callback#code={handoff_code}")
