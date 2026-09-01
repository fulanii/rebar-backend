"""Send a fresh verification code, replacing any previous one."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import CustomUser, EmailVerification
from authentication.serializers import DetailResponseSerializer, ResendVerificationRequestSerializer
from authentication.throttles import CodeRequestRateThrottle
from authentication.utils import issue_code, send_verification_email

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Verifications"],
    summary="Resend the email verification code",
    request=ResendVerificationRequestSerializer,
    responses={200: DetailResponseSerializer},
)
class EmailVerificationResendView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [CodeRequestRateThrottle]

    def post(self, request):
        """
        Send a fresh verification code, replacing any previous one.

        **Endpoint:** POST `auth/resend-verification/`

        **Authentication:** None required

        **Throttle:** 5/hour per IP (`code_request` scope), each call costs an email.

        ---

        ## Request Body (JSON)

        | Field | Type   | Required | Description                       |
        |-------|--------|----------|-----------------------------------|
        | email | string | Yes      | The address to resend the code to. |

        ---

        ## Field Validation Rules

        ### email
        - Required, valid email format. Lowercased and trimmed.

        ---

        ## Responses

        ### 200 OK
        Always returned for a well-formed address, whether or not an account exists
        and whether or not it is already verified. The response deliberately reveals
        nothing about who is registered.

        ```json
        {
            "detail": "If that address needs verification, a new code is on its way."
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
        1. The address is looked up. An unknown or already-verified address does
           nothing at all, and returns the same 200.
        2. A new code replaces the old row, so the **previous code stops working
           immediately**. A user who then finds the older email and types that code
           will be rejected.
        3. Only the raw code is emailed; only the hash is stored.
        """

        serializer = ResendVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = CustomUser.objects.filter(email=email, is_verified=False).first()

        if user is not None:
            code = issue_code(EmailVerification, user)
            send_verification_email(user.email, user.first_name, code)
            logger.info("event=verification_code_resent email=%s", email)
        else:
            logger.info("event=verification_resend_noop email=%s", email)

        return Response(
            {"detail": "If that address needs verification, a new code is on its way."},
            status=status.HTTP_200_OK,
        )
