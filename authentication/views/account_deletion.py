"""Delete your own account."""

import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.serializers import AccountDeletionSerializer
from authentication.throttles import AccountDeletionRateThrottle
from authentication.utils import delete_refresh_cookie, revoke_sessions

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Authentication-Accounts"],
    summary="Delete your account",
    request=AccountDeletionSerializer,
    responses={204: None},
)
class AccountDeletionView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AccountDeletionRateThrottle]

    def post(self, request):
        """
        Permanently delete the signed-in account and everything attached to it.

        **Endpoint:** POST `auth/delete-account/`

        **Authentication:** Bearer access token

        **Throttle:** 5/hour per user (`account_deletion` scope)

        This is a **hard delete** and cannot be undone. The user row goes, and with it
        every row pointing at it -- verification codes, reset codes, pending email
        changes. SimpleJWT keeps its own token rows with a null user; they are opaque
        strings, they are blacklisted first, and they expire on their own.

        Data-protection law expects this to be available and to actually delete. If
        your product needs to retain records instead, see
        `docs/ai/recipes/soft-delete-accounts.md`.

        ---

        ## Request Body (JSON)

        | Field    | Type   | Required     | Description                                 |
        |----------|--------|--------------|---------------------------------------------|
        | email    | string | Yes          | Your own address, typed out to confirm.     |
        | password | string | Conditional  | write_only. Required unless you use Google. |

        ---

        ## Field Validation Rules

        ### email
        - Required. Must match the address on the account exactly, after lowercasing.
          It is a deliberate speed bump on an action with no undo.

        ### password
        - Required for accounts with a password, so a stolen access token is not
          enough on its own.
        - Accounts that sign in with Google have no password to give; the confirmed
          address and a valid token are what they provide.

        ---

        ## Responses

        ### 204 No Content
        The account is gone. The refresh cookie is cleared on the way out.

        ### 400 Bad Request
        ```json
        {
            "email": ["This does not match the email address on your account."],
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
        1. The address is matched and the password confirmed.
        2. Sessions are revoked first, so a request already in flight on another
           device cannot act on a half-deleted account.
        3. The user row is deleted; the codes and pending changes cascade with it.
        4. The refresh cookie is deleted from the browser.
        """

        serializer = AccountDeletionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        email = user.email

        with transaction.atomic():
            revoke_sessions(user)
            user.delete()

        logger.info("event=account_deleted email=%s", email)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        delete_refresh_cookie(response)
        return response
