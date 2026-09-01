"""Confirm a password reset with the emailed code."""

import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import CustomUser, PasswordReset
from authentication.serializers import DetailResponseSerializer, PasswordResetConfirmSerializer
from authentication.throttles import PasswordResetRateThrottle
from authentication.utils import revoke_sessions, send_password_changed_email

from .shared import INVALID_CODE

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Passwords"],
    summary="Confirm a password reset",
    request=PasswordResetConfirmSerializer,
    responses={200: DetailResponseSerializer},
)
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        """
        Set a new password using the emailed reset code.

        **Endpoint:** POST `auth/password-reset/confirm/`

        **Authentication:** None required

        **Throttle:** 5/hour per IP (`password_reset` scope). This limit is what makes
        a 6-digit code safe to guess against.

        ---

        ## Request Body (JSON)

        | Field            | Type   | Required | Description                             |
        |------------------|--------|----------|-----------------------------------------|
        | email            | string | Yes      | The account's email address.            |
        | code             | string | Yes      | The 6-digit code, as a string.          |
        | new_password     | string | Yes      | write_only. Same rules as registration. |
        | confirm_password | string | Yes      | write_only. Must match `new_password`.  |

        ---

        ## Field Validation Rules

        ### code
        - Required, exactly 6 characters, digits only. Send as a string, `"004821"`.

        ### new_password
        - Required, 8-128 characters.
        - Must contain an uppercase letter, a lowercase letter, a digit and a special
          character, identical to the registration rules.

        ### confirm_password
        - Required. Must match `new_password`.

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "detail": "Password updated. You can now sign in with your new password."
        }
        ```

        ### 400 Bad Request
        Wrong, expired, already-used code, or unknown address, one shared message:

        ```json
        {
            "detail": "Invalid or expired reset code."
        }
        ```

        Field-level problems are reported per field:

        ```json
        {
            "new_password": ["Password must contain at least one digit."]
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
        1. `is_valid` rejects a used or expired code before the hash is checked.
        2. The code is compared against the stored hash.
        3. A wrong code is counted. After 5 wrong guesses the code is burned and a
           new one has to be requested, so the 5/hour IP limit is not the only thing
           standing between an attacker and a million combinations.
        4. The code is burned so it cannot be replayed, then the new password is
           hashed and saved.
        5. Every session is revoked: outstanding refresh tokens are blacklisted, and
           the account is stamped so that access tokens issued earlier are refused on
           their next request. A reset usually means someone else is in the account;
           leaving their session alive would defeat the point.
        6. A notification email goes to the account's address.
        """

        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        user = CustomUser.objects.filter(email=email, is_active=True).first()
        reset = PasswordReset.objects.filter(user=user).first() if user else None

        if reset is None or not reset.is_valid:
            logger.info("event=password_reset_failed email=%s", email)
            return Response({"detail": INVALID_CODE}, status=status.HTTP_400_BAD_REQUEST)

        if not reset.check_code(code):
            if reset.register_failure():
                logger.info("event=password_reset_code_exhausted email=%s", email)
            logger.info("event=password_reset_failed email=%s", email)
            return Response({"detail": INVALID_CODE}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            reset.mark_used()
            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=["password"])
            revoked = revoke_sessions(user)

        logger.info("event=password_reset_completed email=%s tokens_revoked=%s", email, revoked)

        send_password_changed_email(user.email, user.first_name)

        return Response(
            {"detail": "Password updated. You can now sign in with your new password."},
            status=status.HTTP_200_OK,
        )
