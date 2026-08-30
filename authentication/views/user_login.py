import logging

from django.contrib.auth.models import update_last_login
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.serializers import UserInfoSerializer, UserLoginRequestSerializer, UserLoginResponseSerializer
from authentication.throttles import LoginRateThrottle
from authentication.utils import set_refresh_cookie

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Tokens"],
    summary="Sign in with email and password",
    request=UserLoginRequestSerializer,
    responses={200: UserLoginResponseSerializer},
)
class UserLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        """
        Exchange an email and password for an access token.

        **Endpoint:** POST `auth/login/`

        **Authentication:** None required

        **Throttle:** 20/hour per IP (`login` scope)

        The response body carries the **access token only**. The refresh token is set
        as an httpOnly cookie scoped to `/token/`, so JavaScript cannot read it and a
        cross-site scripting bug in the frontend cannot steal a week-long session.

        ---

        ## Request Body (JSON)

        | Field    | Type   | Required | Description                     |
        |----------|--------|----------|---------------------------------|
        | email    | string | Yes      | Login address.                  |
        | password | string | Yes      | write_only. Never logged.       |

        ---

        ## Field Validation Rules

        ### email
        - Required, valid email format. Lowercased and trimmed before lookup.

        ### password
        - Required.

        ---

        ## Responses

        ### 200 OK
        Sets the `refresh` cookie (httpOnly, `Path=/token/`).

        ```json
        {
            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user_data": {
                "id": 1,
                "email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "phone_number": "5551234567",
                "is_verified": true,
                "is_active": true,
                "auth_provider": "email",
                "date_joined": "2026-08-29T10:00:00Z"
            }
        }
        ```

        ### 400 Bad Request
        A wrong password and an unregistered address return the **same** message, so
        this endpoint cannot be used to find out which addresses have accounts.

        ```json
        {
            "non_field_errors": ["Incorrect email or password."]
        }
        ```

        An account that exists but has never verified its email is told so, because
        the user needs to know what to do next:

        ```json
        {
            "non_field_errors": ["Please verify your email address before signing in."]
        }
        ```

        ### 401 Unauthorized
        A suspended account is rejected on every request, including this one.

        ```json
        {
            "detail": "Your account is suspended."
        }
        ```

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 3600 seconds."
        }
        ```

        ---

        ## Post-Request Flow
        1. The serializer authenticates the credentials; an inactive (unverified)
           account fails, and is distinguished only after the password is confirmed
           correct.
        2. A refresh/access pair is issued and `last_login` is stamped.
        3. The refresh token is written to the httpOnly cookie and removed from the
           body. Only the access token is returned.
        """

        serializer = UserLoginRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        update_last_login(None, user)

        logger.info("event=login_success email=%s", user.email)

        response = Response(
            {
                "access": str(refresh.access_token),
                "user_data": UserInfoSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
        set_refresh_cookie(response, refresh)
        return response
