"""Finish moving an account to a new email address."""

import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import CustomUser, EmailChange
from authentication.serializers import EmailChangeConfirmResponseSerializer, EmailChangeConfirmSerializer
from authentication.throttles import EmailChangeRateThrottle

from .shared import INVALID_CODE

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Accounts"],
    summary="Confirm an email address change",
    request=EmailChangeConfirmSerializer,
    responses={200: EmailChangeConfirmResponseSerializer},
)
class EmailChangeConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [EmailChangeRateThrottle]

    def post(self, request):
        """
        Move the account to the pending address using the code sent to it.

        **Endpoint:** POST `auth/change-email/confirm/`

        **Authentication:** Bearer access token

        **Throttle:** 5/hour per user (`email_change` scope)

        On success the login address changes. Existing sessions keep working -- you
        are signed in and gave your password to start this, so the sessions are yours.

        ---

        ## Request Body (JSON)

        | Field | Type   | Required | Description                    |
        |-------|--------|----------|--------------------------------|
        | code  | string | Yes      | The 6-digit code, as a string. |

        ---

        ## Field Validation Rules

        ### code
        - Required, exactly 6 characters, digits only. Send as a string -- `"004821"`.
        - Five wrong guesses burn the code; start again at `POST auth/change-email/`.

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "detail": "Email address updated.",
            "email": "new@example.com"
        }
        ```

        ### 400 Bad Request
        Wrong, expired, used or exhausted code, and no pending change, all return the
        same message:

        ```json
        {
            "detail": "Invalid or expired code."
        }
        ```

        If the address was claimed by someone else while the code was in flight:

        ```json
        {
            "detail": "This email address is no longer available."
        }
        ```

        ### 401 Unauthorized
        ```json
        {
            "detail": "Authentication credentials were not provided."
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
        1. `is_valid` rejects a used, expired or exhausted code before the hash check.
        2. A wrong code is counted; the fifth burns it.
        3. Availability is checked again -- the code was issued minutes ago and the
           address may have been verified by someone else since.
        4. The code is burned and the address is updated in one transaction.
        """

        serializer = EmailChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        code = serializer.validated_data["code"]
        change = EmailChange.objects.filter(user=user).first()

        if change is None or not change.is_valid:
            logger.info("event=email_change_failed email=%s", user.email)
            return Response({"detail": INVALID_CODE}, status=status.HTTP_400_BAD_REQUEST)

        if not change.check_code(code):
            if change.register_failure():
                logger.info("event=email_change_code_exhausted email=%s", user.email)
            logger.info("event=email_change_failed email=%s", user.email)
            return Response({"detail": INVALID_CODE}, status=status.HTTP_400_BAD_REQUEST)

        if CustomUser.objects.filter(email=change.new_email, is_verified=True).exclude(pk=user.pk).exists():
            logger.info("event=email_change_failed email=%s reason=taken", user.email)
            return Response(
                {"detail": "This email address is no longer available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous = user.email

        with transaction.atomic():
            change.mark_used()
            user.email = change.new_email
            user.save(update_fields=["email"])

        logger.info("event=email_changed from=%s to=%s", previous, user.email)

        return Response({"detail": "Email address updated.", "email": user.email}, status=status.HTTP_200_OK)
