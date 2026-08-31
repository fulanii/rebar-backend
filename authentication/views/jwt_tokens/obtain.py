"""The standard SimpleJWT credentials-for-tokens endpoint."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from authentication.serializers import TokenObtainPairResponseSerializer
from authentication.throttles import LoginRateThrottle
from authentication.utils import set_refresh_cookie

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Tokens"],
    summary="Obtain a token pair",
    responses={200: TokenObtainPairResponseSerializer},
)
class CustomTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
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
