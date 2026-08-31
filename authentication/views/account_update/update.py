"""Change the name on your own account."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.serializers import ProfileUpdateSerializer, UserInfoSerializer
from authentication.throttles import ProfileUpdateRateThrottle

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Accounts"],
    summary="Update your name",
    request=ProfileUpdateSerializer,
    responses={200: UserInfoSerializer},
)
class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ProfileUpdateRateThrottle]

    def patch(self, request):
        """
        Change the first or last name on the signed-in account.

        **Endpoint:** PATCH `auth/me/update/`

        **Authentication:** Bearer access token

        **Throttle:** 20/hour per user (`profile_update` scope)

        Only the fields a person may change about themselves without proving anything
        new. The **email address** is the login and moves through
        `POST auth/change-email/`, which needs the password and a code sent to the new
        address. The **phone number** is left out on purpose: it is collected at
        registration and, once you add SMS verification, changing it has to prove
        ownership the same way an email change does. Adding it here first would mean
        taking it away again later.

        ---

        ## Request Body (JSON)

        | Field      | Type   | Required | Description                        |
        |------------|--------|----------|------------------------------------|
        | first_name | string | No       | Given name. Trimmed.               |
        | last_name  | string | No       | Family name. Trimmed.              |

        Send either or both. A body with neither is rejected rather than treated as a
        no-op, so a request that changes nothing is never mistaken for one that worked.

        ---

        ## Field Validation Rules

        ### first_name / last_name
        - At least 2 characters after trimming.
        - Letters (any alphabet), spaces, hyphens and apostrophes only.
        - Identical to the rules registration applies, so a name that was valid at
          signup cannot become invalid here.

        ---

        ## Responses

        ### 200 OK
        The full profile, in the same shape `GET auth/me/` returns, so a client can
        replace its cached user object with the response.

        ```json
        {
            "id": 1,
            "email": "jane@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "5551234567",
            "is_verified": true,
            "is_active": true,
            "auth_provider": "email",
            "date_joined": "2026-01-14T09:20:11.482913Z"
        }
        ```

        ### 400 Bad Request
        ```json
        {
            "first_name": ["First name must be at least 2 characters."]
        }
        ```

        ```json
        {
            "non_field_errors": ["Send at least one field to change."]
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
        1. Only the fields present in the body are validated and written; anything
           omitted is left alone.
        2. Sessions are untouched. Nothing here changes how the account is signed in
           to, so there is nothing to revoke.
        """

        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        logger.info("event=profile_updated email=%s fields=%s", user.email, ",".join(serializer.validated_data))

        return Response(UserInfoSerializer(user).data, status=status.HTTP_200_OK)
