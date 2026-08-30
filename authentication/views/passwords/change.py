"""Change the password of a signed-in user."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.serializers import DetailResponseSerializer, PasswordChangeSerializer
from authentication.throttles import UserInfoRateThrottle

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Passwords"],
    summary="Change password while signed in",
    request=PasswordChangeSerializer,
    responses={200: DetailResponseSerializer},
)
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserInfoRateThrottle]

    def post(self, request):
        """
        Change the signed-in user's password.

        **Endpoint:** POST `auth/change-password/`

        **Authentication:** JWT required

        **Throttle:** 60/minute per user (`user_info` scope)

        ---

        ## Request Body (JSON)

        | Field            | Type   | Required | Description                              |
        |------------------|--------|----------|------------------------------------------|
        | current_password | string | Yes      | write_only. Proves it is really you.     |
        | new_password     | string | Yes      | write_only. Same rules as registration.  |
        | confirm_password | string | Yes      | write_only. Must match `new_password`.   |

        ---

        ## Field Validation Rules

        ### current_password
        - Required, and must match the account's current password. This is checked
          even though the request is authenticated: it stops someone with a stolen
          access token, or an unattended laptop, from locking the owner out.

        ### new_password
        - Required, 8-128 characters, upper + lower + digit + special.
        - Must differ from the current password.

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "detail": "Password changed."
        }
        ```

        ### 400 Bad Request
        ```json
        {
            "current_password": ["Current password is incorrect."]
        }
        ```

        ```json
        {
            "new_password": ["New password must be different from the current one."]
        }
        ```

        ### 401 Unauthorized
        ```json
        {
            "detail": "Authentication credentials were not provided."
        }
        ```

        ---

        ## Post-Request Flow
        1. The current password is verified against the stored hash.
        2. The new password is hashed and saved.

        > **Note:** other sessions are **not** signed out. See the note on the reset
        > endpoint above if you need that behaviour.
        """

        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        logger.info("event=password_changed email=%s", user.email)
        return Response({"detail": "Password changed."}, status=status.HTTP_200_OK)
