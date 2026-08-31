"""Request a password reset code."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import CustomUser, PasswordReset
from authentication.serializers import DetailResponseSerializer, PasswordResetRequestSerializer
from authentication.throttles import PasswordResetRateThrottle
from authentication.utils import issue_code, send_password_reset_email

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Passwords"],
    summary="Request a password reset code",
    request=PasswordResetRequestSerializer,
    responses={200: DetailResponseSerializer},
)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        """
        Email a 6-digit code that authorizes choosing a new password.

        **Endpoint:** POST `auth/password-reset/`

        **Authentication:** None required

        **Throttle:** 5/hour per IP (`password_reset` scope)

        ---

        ## Request Body (JSON)

        | Field | Type   | Required | Description                    |
        |-------|--------|----------|--------------------------------|
        | email | string | Yes      | The account's email address.   |

        ---

        ## Field Validation Rules

        ### email
        - Required, valid email format. Lowercased and trimmed.

        ---

        ## Responses

        ### 200 OK
        Always returned for a well-formed address, whether or not an account exists.
        A "no such user" response here would turn this endpoint into a way to test
        whether any given address is registered.

        ```json
        {
            "detail": "If an account exists for that address, a reset code is on its way."
        }
        ```

        ### 400 Bad Request
        ```json
        {
            "email": ["Enter a valid email address."]
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
        1. The address is looked up. Unknown addresses do nothing and still return 200.
        2. Accounts created through Google have no usable password; they are skipped,
           since a reset code would set a password on an account that signs in another
           way. Those users keep using Google.
        3. A new code replaces any previous one, so an older reset email stops working.
        4. Only the raw code is emailed; only the hash is stored.
        """

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = CustomUser.objects.filter(email=email, is_active=True).first()

        if user is not None and user.has_usable_password():
            code = issue_code(PasswordReset, user)
            send_password_reset_email(user.email, user.first_name, code)
            logger.info("event=password_reset_requested email=%s", email)
        else:
            logger.info("event=password_reset_noop email=%s", email)

        return Response(
            {"detail": "If an account exists for that address, a reset code is on its way."},
            status=status.HTTP_200_OK,
        )
