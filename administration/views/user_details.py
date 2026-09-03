"""One account in full, for support and operations."""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAdminUser

from administration.serializers import UserDetailResponseSerializer
from administration.throttles import AdminReadRateThrottle
from authentication.models import CustomUser


@extend_schema(
    tags=["Administration-Users"],
    summary="Get one user account",
    responses={200: UserDetailResponseSerializer},
)
class UserDetailView(RetrieveAPIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminReadRateThrottle]
    serializer_class = UserDetailResponseSerializer
    queryset = CustomUser.objects.all()
    lookup_url_kwarg = "user_id"

    def get(self, request, *args, **kwargs):
        """
        One account, by id.

        **Endpoint:** GET `admin/users/{user_id}/`

        **Authentication:** JWT required, and the account must be staff

        **Throttle:** 120/minute per account (`admin_read` scope), shared with the list

        The support view of a single person: what state their account is in, how they
        sign in, and whether their sessions have been revoked. Read-only. Everything
        that changes an account is its own endpoint, so that each one can be audited
        for what it did rather than for what it touched.

        Like the list, this deliberately confirms whether an address is registered,
        which the endpoints under `auth/` refuse to do. A missing id returns 404, and
        that 404 is itself an answer, which is why the route is useless without the
        staff check above.

        Takes **no body and no query parameters**.

        ---

        ## Path parameters

        | Name | Type | Description |
        |---|---|---|
        | `user_id` | integer | The **account to read**, as `id` from `admin/users/`. |

        ---

        ## Responses

        ### 200 OK
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

        `sessions_revoked_at` is `null` until something signs the account out
        everywhere, a completed password reset, say.

        ### 401 Unauthorized
        Missing, malformed or expired access token:

        ```json
        {
            "detail": "Authentication credentials were not provided."
        }
        ```

        ### 403 Forbidden
        A signed-in account that is not staff:

        ```json
        {
            "detail": "You do not have permission to perform this action."
        }
        ```

        ### 404 Not Found
        No account with that id, including one deleted a moment ago:

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

        return super().get(request, *args, **kwargs)
