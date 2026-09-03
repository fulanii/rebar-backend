"""Suspending one account, and lifting it again."""

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from administration.models import Suspension
from administration.permissions import IsSuperUser
from administration.serializers import SuspensionRequestSerializer, SuspensionResponseSerializer
from administration.throttles import AdminWriteRateThrottle
from authentication.models import CustomUser


@extend_schema(
    tags=["Administration-Users"],
    summary="Suspend or reinstate one user account",
    request=SuspensionRequestSerializer,
    responses={200: SuspensionResponseSerializer, 201: SuspensionResponseSerializer},
)
class SuspensionView(GenericAPIView):
    permission_classes = [IsSuperUser]
    throttle_classes = [AdminWriteRateThrottle]
    serializer_class = SuspensionRequestSerializer
    queryset = CustomUser.objects.all()
    lookup_url_kwarg = "user_id"

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "target": self.get_object()}

    def post(self, request, *args, **kwargs):
        """
        Suspend an account, with a reason.

        **Endpoint:** POST `admin/users/{user_id}/suspension/`

        **Authentication:** JWT required, and the account must be a **superuser**

        **Throttle:** 60/minute per account (`admin_write` scope)

        Takes effect on the account's very next request, including one carrying an
        access token minted a second ago: `SuspensionAwareJWTAuthentication` reads the
        flag on every request rather than trusting the token. Nothing needs revoking,
        and nothing has to wait for a token to expire.

        Suspending writes a row rather than only flipping a flag, so an account
        suspended and reinstated three times has three rows saying who did it and why.
        You cannot suspend your own account, and an account already suspended has to be
        reinstated before it can be suspended again.

        ---

        ## Path parameters

        | Name | Type | Description |
        |---|---|---|
        | `user_id` | integer | The **account being suspended**, as `id` from `admin/users/`. |

        Not a suspension id. No suspension record exists yet; this call is what creates one.

        ---

        ## Body

        | Field | Type | Notes |
        |---|---|---|
        | `reason` | string | One of `spam`, `fraud`, `chargeback`, `abuse`, `tos`, `manual`. Defaults to `manual`. |
        | `notes` | string | Optional. Where the ticket number goes. |

        ---

        ## Responses

        ### 201 Created
        ```json
        {
            "id": 7,
            "user": 42,
            "reason": "fraud",
            "notes": "chargeback ring, ticket SUP-1183",
            "suspended_at": "2026-09-03T09:12:00Z",
            "suspended_by": "root@example.com",
            "lifted_at": null,
            "lifted_by": null
        }
        ```

        ### 400 Bad Request
        ```json
        {
            "non_field_errors": ["This account is already suspended."]
        }
        ```

        ```json
        {
            "non_field_errors": ["You cannot suspend your own account."]
        }
        ```

        ### 401 Unauthorized
        ```json
        {
            "detail": "Authentication credentials were not provided."
        }
        ```

        ### 403 Forbidden
        A signed-in account that is not a superuser, staff included:

        ```json
        {
            "detail": "You do not have permission to perform this action."
        }
        ```

        ### 404 Not Found
        ```json
        {
            "detail": "No CustomUser matches the given query."
        }
        ```

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```
        """

        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            suspension = Suspension.objects.create(user=user, suspended_by=request.user, **serializer.validated_data)
            user.is_suspended = True
            user.save(update_fields=["is_suspended"])

        return Response(SuspensionResponseSerializer(suspension).data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        """
        Lift the suspension on an account.

        **Endpoint:** DELETE `admin/users/{user_id}/suspension/`

        **Authentication:** JWT required, and the account must be a **superuser**

        **Throttle:** 60/minute per account (`admin_write` scope)

        Closes the open record rather than deleting it, stamping who lifted it and
        when, and clears the flag so the account can sign in again. The history stays.

        The account is signed out either way: suspension refused its requests, and
        lifting does not restore a session it never kept. Whoever owns it signs in
        again as normal.

        Takes **no body**. The open record is found from the account, because an account
        can only have one at a time.

        ---

        ## Path parameters

        | Name | Type | Description |
        |---|---|---|
        | `user_id` | integer | The **account being reinstated**, as `id` from `admin/users/`. |

        Not the `id` of the suspension record in the response body. That id is never a
        path parameter anywhere in this API.

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "id": 7,
            "user": 42,
            "reason": "fraud",
            "notes": "chargeback ring, ticket SUP-1183",
            "suspended_at": "2026-09-03T09:12:00Z",
            "suspended_by": "root@example.com",
            "lifted_at": "2026-09-04T11:40:00Z",
            "lifted_by": "root@example.com"
        }
        ```

        ### 400 Bad Request
        ```json
        {
            "non_field_errors": ["This account is not suspended."]
        }
        ```

        ### 401 Unauthorized
        ```json
        {
            "detail": "Authentication credentials were not provided."
        }
        ```

        ### 403 Forbidden
        ```json
        {
            "detail": "You do not have permission to perform this action."
        }
        ```

        ### 404 Not Found
        ```json
        {
            "detail": "No CustomUser matches the given query."
        }
        ```

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```
        """

        user = self.get_object()
        suspension = user.suspensions.filter(lifted_at__isnull=True).first()

        if suspension is None:
            return Response(
                {"non_field_errors": ["This account is not suspended."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            suspension.lifted_at = timezone.now()
            suspension.lifted_by = request.user
            suspension.save(update_fields=["lifted_at", "lifted_by"])
            user.is_suspended = False
            user.save(update_fields=["is_suspended"])

        return Response(SuspensionResponseSerializer(suspension).data, status=status.HTTP_200_OK)
