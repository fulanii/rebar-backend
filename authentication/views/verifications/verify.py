"""Activate an account with the emailed code."""

import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import CustomUser, EmailVerification
from authentication.serializers import DetailResponseSerializer, EmailVerificationRequestSerializer
from authentication.throttles import CodeSubmitRateThrottle

from .shared import INVALID_CODE

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Verifications"],
    summary="Verify email with a 6-digit code",
    request=EmailVerificationRequestSerializer,
    responses={200: DetailResponseSerializer},
)
class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [CodeSubmitRateThrottle]

    def post(self, request):
        """
        Activate an account with the code emailed at registration.

        **Endpoint:** POST `auth/verify-email/`

        **Authentication:** None required

        **Throttle:** 5/hour per IP (`code_submit` scope)

        The rate limit is what makes a 6-digit code safe. A million combinations at
        five attempts an hour is not a viable attack; without the limit it is minutes
        of scripted guessing.

        ---

        ## Request Body (JSON)

        | Field | Type   | Required | Description                          |
        |-------|--------|----------|--------------------------------------|
        | email | string | Yes      | The address the code was sent to.    |
        | code  | string | Yes      | The 6-digit code, as a string.       |

        ---

        ## Field Validation Rules

        ### email
        - Required, valid email format. Lowercased and trimmed.

        ### code
        - Required, exactly 6 characters, digits only.
        - Send it as a **string**: `"004821"`. As a number the leading zeros are lost
          and the code will not match.

        ---

        ## Responses

        ### 200 OK
        The account is now active and verified, and can sign in.

        ```json
        {
            "detail": "Email verified. You can now sign in."
        }
        ```

        ### 400 Bad Request
        Wrong code, expired code, already-used code, or unknown address -- all return
        the same body on purpose, so this endpoint cannot be used to discover which
        addresses have accounts.

        ```json
        {
            "detail": "Invalid or expired verification code."
        }
        ```

        Malformed input is reported per field:

        ```json
        {
            "code": ["Enter the 6-digit code from your email."]
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
        1. The user and their verification row are looked up.
        2. `is_valid` rejects a used or expired code before the hash is checked.
        3. The submitted code is compared against the stored **hash**.
        4. On success the code is burned (`used=True`) so it cannot be replayed, and
           the account is set active and verified.
        """

        serializer = EmailVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        user = CustomUser.objects.filter(email=email).first()
        verification = EmailVerification.objects.filter(user=user).first() if user else None

        if verification is None or not verification.is_valid or not verification.check_code(code):
            logger.info("event=email_verification_failed email=%s", email)
            return Response({"detail": INVALID_CODE}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            verification.mark_used()
            user.is_active = True
            user.is_verified = True
            user.save(update_fields=["is_active", "is_verified"])

        logger.info("event=email_verified email=%s", email)
        return Response({"detail": "Email verified. You can now sign in."}, status=status.HTTP_200_OK)
