"""Start moving an account to a new email address."""

import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import EmailChange
from authentication.serializers import DetailResponseSerializer, EmailChangeRequestSerializer
from authentication.throttles import EmailChangeRateThrottle
from authentication.utils import issue_code, send_email_change_email

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Accounts"],
    summary="Request an email address change",
    request=EmailChangeRequestSerializer,
    responses={200: DetailResponseSerializer},
)
class EmailChangeRequestView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [EmailChangeRateThrottle]

    def post(self, request):
        """
        Email a 6-digit code to the address you want to move the account to.

        **Endpoint:** POST `auth/change-email/`

        **Authentication:** Bearer access token

        **Throttle:** 5/hour per user (`email_change` scope)

        The address on the account does not change here. It changes when the code is
        submitted to `POST auth/change-email/confirm/`, which is what proves the new
        address is yours -- the same proof registration asks for.

        ---

        ## Request Body (JSON)

        | Field     | Type   | Required | Description                            |
        |-----------|--------|----------|----------------------------------------|
        | new_email | string | Yes      | The address to move to.                |
        | password  | string | Yes      | write_only. Your current password.     |

        ---

        ## Field Validation Rules

        ### new_email
        - Required, valid email format. Lowercased and trimmed.
        - Must not be the address already on the account.
        - Must not belong to a **verified** account.

        ### password
        - Required. Your current password, even though the request is authenticated --
          an access token alone must not be enough to take over the login address.
        - Accounts that sign in with Google have no password and cannot use this
          endpoint; changing the address would break the link to the Google identity.

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "detail": "Check your new email address for a 6-digit code."
        }
        ```

        ### 400 Bad Request
        ```json
        {
            "new_email": ["This email address is not available."],
            "password": ["Password is incorrect."]
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
        1. The password is confirmed and the new address is checked for availability.
        2. One `EmailChange` row per user is written, so asking again replaces the
           pending address and the previous code stops working.
        3. The code is emailed to the **new** address only. Sending it to the current
           one would prove nothing about the new one.
        """

        serializer = EmailChangeRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_email = serializer.validated_data["new_email"]

        with transaction.atomic():
            code = issue_code(EmailChange, user)
            EmailChange.objects.filter(user=user).update(new_email=new_email)

        logger.info("event=email_change_requested email=%s", user.email)

        send_email_change_email(new_email, user.first_name, code)

        return Response(
            {"detail": "Check your new email address for a 6-digit code."},
            status=status.HTTP_200_OK,
        )
