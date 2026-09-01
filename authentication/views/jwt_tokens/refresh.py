"""Minting a new access token from the refresh cookie."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from authentication.serializers import TokenRefreshResponseSerializer
from authentication.throttles import TokenRefreshRateThrottle
from authentication.utils import get_refresh_cookie, set_refresh_cookie

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Tokens"],
    summary="Refresh the access token",
    request=None,
    responses={200: TokenRefreshResponseSerializer},
)
class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_classes = [TokenRefreshRateThrottle]

    def post(self, request, *args, **kwargs):
        """
        Mint a new access token from the refresh cookie.

        **Endpoint:** POST `token/refresh/`

        **Authentication:** None required, the refresh cookie *is* the credential.

        **Throttle:** 30/minute per IP (`token_refresh` scope). Higher than the other
        limits because clients refresh on a timer.

        ---

        ## Request Body

        **None.** The refresh token is read from the httpOnly `refresh` cookie, not
        from the body. Send the request with credentials included
        (`fetch(url, { credentials: "include" })`) or the browser will not attach it.

        ---

        ## Responses

        ### 200 OK
        Rotation is enabled, so this also issues a **new** refresh token and writes it
        straight back into the cookie. The token it replaces is blacklisted, which is
        what limits the damage of a stolen refresh token to a single use.

        ```json
        {
            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
        ```

        ### 401 Unauthorized
        No cookie, or a token that is expired, malformed, or already rotated away:

        ```json
        {
            "detail": "No refresh token cookie found."
        }
        ```

        ```json
        {
            "detail": "Token is invalid or expired",
            "code": "token_not_valid"
        }
        ```
        """

        refresh_token = get_refresh_cookie(request)

        if not refresh_token:
            return Response(
                {"detail": "No refresh token cookie found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = request.data.copy()
        data["refresh"] = refresh_token
        request._full_data = data

        response = super().post(request, *args, **kwargs)

        rotated = response.data.pop("refresh", None) if response.status_code == status.HTTP_200_OK else None

        if rotated:
            set_refresh_cookie(response, rotated)

        return response
