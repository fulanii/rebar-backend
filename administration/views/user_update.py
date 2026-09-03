"""Correcting one account on someone's behalf."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from administration.permissions import IsSuperUser
from administration.serializers import UserDetailResponseSerializer, UserUpdateRequestSerializer
from administration.throttles import AdminWriteRateThrottle
from authentication.models import CustomUser


@extend_schema(
    tags=["Administration-Users"],
    summary="Update one user account",
    request=UserUpdateRequestSerializer,
    responses={200: UserDetailResponseSerializer},
)
class UserUpdateView(GenericAPIView):
    permission_classes = [IsSuperUser]
    throttle_classes = [AdminWriteRateThrottle]
    serializer_class = UserUpdateRequestSerializer
    queryset = CustomUser.objects.all()
    lookup_url_kwarg = "user_id"

    def patch(self, request, *args, **kwargs):
        """
        Change one account on its owner's behalf.

        **Endpoint:** PATCH `admin/users/{user_id}/update/`

        **Authentication:** JWT required, and the account must be a **superuser**

        **Throttle:** 60/minute per account (`admin_write` scope)

        Staff alone is not enough. Everything on this endpoint either moves the login
        itself or hands out access to this API, so the whole route sits behind the
        superuser check rather than guarding the two dangerous fields inside it.

        Partial: send only what changes. There is no PUT, because a full replacement of
        an account is never what support means to do, and a forgotten field would clear
        a flag nobody was looking at.

        **No password field, deliberately.** An operator who can set a password can sign
        in as the customer, and the audit trail cannot tell that apart from support
        work. Send the customer a reset instead, so they prove the address themselves.

        ---

        ## Path parameters

        | Name | Type | Description |
        |---|---|---|
        | `user_id` | integer | The **account being edited**, as `id` from `admin/users/`. |

        Never the id of the superuser making the call.

        ---

        ## Body

        | Field | Type | Notes |
        |---|---|---|
        | `email` | string | The login itself. Lowercased, and must not belong to another account. |
        | `first_name` | string | |
        | `last_name` | string | |
        | `phone_number` | string | 10-digit US number, or `""` to clear it. |
        | `is_active` | boolean | Whether the account may sign in at all. |
        | `is_verified` | boolean | Whether the address is treated as proven. |
        | `is_staff` | boolean | Grants this API. Never on your own account. |
        | `is_superuser` | boolean | Grants everything, including this endpoint. Never on your own account. |

        Changing `email` does **not** reset `is_verified`. Correcting a typo for someone
        who is on the phone is not the same as an unproven address, so the two are set
        separately and on purpose.

        `is_active` is what Django's own authentication checks, so clearing it signs the
        account out of every future request. It does not revoke tokens already issued.

        ---

        ## Responses

        ### 200 OK
        The full account, in the same shape as `admin/users/{user_id}/`:

        ```json
        {
            "id": 42,
            "email": "jane@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "5551234567",
            "is_active": true,
            "is_verified": true,
            "is_suspended": false,
            "is_staff": false,
            "is_superuser": false,
            "auth_provider": "email",
            "date_joined": "2026-09-01T10:00:00Z",
            "last_login": "2026-09-02T08:14:00Z",
            "sessions_revoked_at": null
        }
        ```

        ### 400 Bad Request
        An empty body:

        ```json
        {
            "non_field_errors": ["Send at least one field to change."]
        }
        ```

        An address that belongs to somebody else:

        ```json
        {
            "email": ["An account with this email already exists."]
        }
        ```

        Editing your own staff or superuser access, at any level:

        ```json
        {
            "non_field_errors": ["You cannot change your own staff or superuser access."]
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
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(UserDetailResponseSerializer(user).data, status=status.HTTP_200_OK)
