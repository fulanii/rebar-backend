"""Trade the single-use handoff code for an access token."""

from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.serializers import GoogleOAuthExchangeRequestSerializer, GoogleOAuthExchangeResponseSerializer
from authentication.throttles import GoogleAuthRateThrottle
from authentication.utils import set_refresh_cookie

from .shared import EXCHANGE_CACHE_PREFIX


@extend_schema(
    tags=["Authentication-Google"],
    summary="Exchange the Google handoff code for tokens",
    request=GoogleOAuthExchangeRequestSerializer,
    responses={200: GoogleOAuthExchangeResponseSerializer},
)
class GoogleOAuthExchangeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [GoogleAuthRateThrottle]

    def post(self, request):
        """
        Trade the single-use handoff code for an access token.

        **Endpoint:** POST `auth/google/exchange/`

        **Authentication:** None required, the handoff code is the credential.

        **Throttle:** 20/hour per IP (`google_auth` scope)

        The frontend reads `code` from the URL fragment it was redirected to and posts
        it here. The response is the same shape as a password login.

        ---

        ## Request Body (JSON)

        | Field | Type   | Required | Description                                     |
        |-------|--------|----------|-------------------------------------------------|
        | code  | string | Yes      | The one-time code from the callback fragment.   |

        ---

        ## Field Validation Rules

        ### code
        - Required.
        - Single-use and valid for 2 minutes. Consumed on first use, so a second
          attempt with the same code always fails.

        ---

        ## Responses

        ### 200 OK
        Sets the `refresh` cookie (httpOnly, `Path=/token/`); only the access token is
        in the body.

        ```json
        {
            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user_data": {
                "id": 7,
                "email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "phone_number": "",
                "is_verified": true,
                "is_active": true,
                "auth_provider": "google",
                "date_joined": "2026-08-29T10:00:00Z"
            }
        }
        ```

        `phone_number` is empty for Google sign-ups: Google does not give us one, and
        only the registration form requires it.

        ### 400 Bad Request
        Missing, expired, or already-used code:

        ```json
        {
            "detail": "Invalid or expired code."
        }
        ```

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 3600 seconds."
        }
        ```
        """

        serializer = GoogleOAuthExchangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cache_key = f"{EXCHANGE_CACHE_PREFIX}{serializer.validated_data['code']}"
        payload = cache.get(cache_key)

        if payload is None:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(cache_key)

        refresh = payload.pop("refresh", None)

        response = Response(payload, status=status.HTTP_200_OK)
        set_refresh_cookie(response, refresh)
        return response
