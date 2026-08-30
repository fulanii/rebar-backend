"""SimpleJWT's token views, wrapped so the refresh token lives in an httpOnly cookie."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from authentication.serializers import TokenObtainPairResponseSerializer, TokenRefreshResponseSerializer
from authentication.throttles import LoginRateThrottle, TokenRefreshRateThrottle
from authentication.utils import delete_refresh_cookie, get_refresh_cookie, set_refresh_cookie

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Tokens"],
    summary="Obtain a token pair",
    responses={200: TokenObtainPairResponseSerializer},
)
class CustomTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        """
        Exchange credentials for an access token, setting the refresh cookie.

        **Endpoint:** POST `token/`

        **Authentication:** None required

        **Throttle:** 20/hour per IP (`login` scope)

        The standard SimpleJWT endpoint. Prefer `POST auth/login/`, which returns the
        user profile alongside the token; this one exists for tooling that expects the
        conventional path.

        ---

        ## Request Body (JSON)

        | Field    | Type   | Required | Description               |
        |----------|--------|----------|---------------------------|
        | email    | string | Yes      | Login address.            |
        | password | string | Yes      | write_only.               |

        ---

        ## Responses

        ### 200 OK
        Sets the `refresh` cookie (httpOnly, `Path=/token/`). The refresh token is
        removed from the body.

        ```json
        {
            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
        ```

        ### 401 Unauthorized
        ```json
        {
            "detail": "No active account found with the given credentials."
        }
        ```
        """

        response = super().post(request, *args, **kwargs)

        refresh = response.data.pop("refresh", None) if response.status_code == status.HTTP_200_OK else None

        if refresh:
            set_refresh_cookie(response, refresh)

        return response


@extend_schema(
    tags=["Authentication-Tokens"],
    summary="Refresh the access token",
    request=None,
    responses={200: TokenRefreshResponseSerializer},
)
class CustomTokenRefreshView(TokenRefreshView):
    throttle_classes = [TokenRefreshRateThrottle]

    def post(self, request, *args, **kwargs):
        """
        Mint a new access token from the refresh cookie.

        **Endpoint:** POST `token/refresh/`

        **Authentication:** None required -- the refresh cookie *is* the credential.

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


@extend_schema(
    tags=["Authentication-Tokens"],
    summary="Sign out (blacklist the refresh token)",
    request=None,
    responses={205: None},
)
class CustomTokenBlacklistView(TokenRefreshView):
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
