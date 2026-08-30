import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import EmailVerification
from authentication.serializers import UserRegistrationRequestSerializer, UserRegistrationResponseSerializer
from authentication.throttles import RegistrationRateThrottle
from authentication.utils import issue_code, send_verification_email

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Accounts"],
    summary="Register a new account",
    request=UserRegistrationRequestSerializer,
    responses={201: UserRegistrationResponseSerializer},
)
class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegistrationRateThrottle]

    def post(self, request):
        """
        Create an account and email a 6-digit verification code.

        **Endpoint:** POST `auth/register/`

        **Authentication:** None required

        **Throttle:** 5/hour per IP (`registration` scope)

        The account is created **inactive** and cannot sign in until the emailed code
        is submitted to `POST auth/verify-email/`. No tokens are returned here.

        ---

        ## Request Body (JSON)

        | Field            | Type   | Required | Description                                      |
        |------------------|--------|----------|--------------------------------------------------|
        | email            | string | Yes      | Login address. Lowercased and trimmed.           |
        | first_name       | string | Yes      | Given name.                                      |
        | last_name        | string | Yes      | Family name.                                     |
        | phone_number     | string | Yes      | US number, any format. Stored as 10 digits.      |
        | password         | string | Yes      | write_only. Never returned or logged.            |
        | confirm_password | string | Yes      | write_only. Must match `password`.               |

        ---

        ## Field Validation Rules

        ### email
        - Required, valid email format.
        - Lowercased and stripped before the uniqueness check.
        - Must not belong to a **verified** account.
        - An **unverified** account with this address is taken over: its details and
          password are replaced by the ones sent here and a new code is emailed.
          Nobody proved they owned that address, so nobody can hold it hostage by
          registering it and never verifying.

        ### first_name / last_name
        - Required, at least 2 characters after trimming.
        - Letters (any alphabet), spaces, hyphens and apostrophes only.

        ### phone_number
        - Required. Non-digits are stripped, so `(555) 123-4567` and `+1 555 123 4567`
          are both accepted.
        - A leading `1` country code is removed; the result must be exactly 10 digits.
        - Area code and exchange code may not begin with 0 or 1.
        - Stored as raw digits, e.g. `"5551234567"`.

        ### password
        - Required, 8-128 characters.
        - Must contain an uppercase letter, a lowercase letter, a digit and a special
          character. All failures are reported at once.

        ### confirm_password
        - Required. Must match `password` exactly.

        ---

        ## Responses

        ### 201 Created
        The account exists but is inactive; a code is on its way.

        ```json
        {
            "detail": "Account created. Check your email for a 6-digit verification code.",
            "email": "jane@example.com"
        }
        ```

        ### 400 Bad Request
        One entry per invalid field.

        ```json
        {
            "email": ["An account with this email already exists."],
            "phone_number": ["Enter a valid 10-digit US phone number."]
        }
        ```

        Password rules are returned as a list:

        ```json
        {
            "password": [
                "Password must contain at least one uppercase letter.",
                "Password must contain at least one special character."
            ]
        }
        ```

        Cross-field errors are keyed to the field that has to change:

        ```json
        {
            "confirm_password": ["Passwords do not match."]
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
        1. Serializer validates every field and creates the user with a hashed
           password, or overwrites an existing unverified account with the same
           address.
        2. A cryptographically strong 6-digit code is generated.
        3. `EmailVerification` is written with `update_or_create`, so a user always has
           exactly one live code -- issuing a new one invalidates any previous code.
        4. Only the **raw** code is emailed; only its **hash** is stored.
        5. Email failures are logged but do not fail the request; the user can ask for
           another code at `POST auth/resend-verification/`.
        """

        serializer = UserRegistrationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()
            code = issue_code(EmailVerification, user)

        logger.info("event=user_registered email=%s", user.email)

        # Outside the transaction: emailing a code for a user that then rolls back
        # would send someone a code for an account that does not exist.
        send_verification_email(user.email, user.first_name, code)

        return Response(
            {
                "detail": "Account created. Check your email for a 6-digit verification code.",
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )
