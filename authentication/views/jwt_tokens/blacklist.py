"""Signing out: blacklisting the refresh token and clearing the cookie."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from authentication.throttles import TokenRefreshRateThrottle
from authentication.utils import delete_refresh_cookie, get_refresh_cookie

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Tokens"],
    summary="Sign out (blacklist the refresh token)",
    request=None,
    responses={205: None},
)
class CustomTokenBlacklistView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_classes = [TokenRefreshRateThrottle]

    def post(self, request, *args, **kwargs):
        """
        Sign out: blacklist the refresh token and clear the cookie.

        **Endpoint:** POST `token/blacklist/`

        **Authentication:** None required -- the refresh cookie is the credential.

        **Throttle:** 30/minute per IP (`token_refresh` scope)

        Blacklisting is what makes logout real. Without it the refresh token stays
        valid for its full seven days, and clearing the cookie only removes the
        browser's copy -- anyone who captured the token could keep using it.

        The already-issued **access** token keeps working until it expires (up to 30
        minutes). To cut someone off immediately, suspend the account: that is checked
        on every request. See `authentication/auth.py`.

        ---

        ## Request Body

        **None.** The refresh token is read from the httpOnly `refresh` cookie.

        ---

        ## Responses

        ### 205 Reset Content
        Signed out. The `refresh` cookie is deleted. Returned even when there was no
        cookie or the token was already invalid -- logout is idempotent and should
        never fail the client.

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```

        ---

        ## Post-Request Flow
        1. The refresh token is read from the cookie.
        2. It is added to the blacklist so it can never be exchanged again.
        3. The cookie is deleted -- with the exact same name, path and domain used to
           set it, or the browser would keep it.
        """

        refresh_token = get_refresh_cookie(request)

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
                logger.info("event=logout_success")
            except TokenError:
                logger.info("event=logout_token_already_invalid")

        response = Response(status=status.HTTP_205_RESET_CONTENT)
        delete_refresh_cookie(response)
        return response
