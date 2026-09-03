"""Every account in the system, for support and operations."""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser

from administration.pagination import UserCursorPagination
from administration.serializers import UserListResponseSerializer
from administration.throttles import AdminReadRateThrottle
from authentication.models import CustomUser


@extend_schema(
    tags=["Administration-Users"],
    summary="List every user account",
    responses={200: UserListResponseSerializer(many=True)},
)
class UserListView(ListAPIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminReadRateThrottle]
    pagination_class = UserCursorPagination
    serializer_class = UserListResponseSerializer
    queryset = CustomUser.objects.all()

    def get(self, request, *args, **kwargs):
        """
        Every account, newest signup first.

        **Endpoint:** GET `admin/users/`

        **Authentication:** JWT required, and the account must be staff

        **Throttle:** 120/minute per account (`admin_read` scope)

        Cursor paginated, not page numbered. The list changes while it is being read,
        and a page number would show a row twice or skip it entirely once a new signup
        shifts everything down. Follow `next` rather than building a cursor yourself,
        the value is opaque and its format is not part of this contract.

        Deliberately reveals whether an address is registered, which the endpoints under
        `auth/` refuse to do. That is the point of this one, and it is why the route is
        useless without the staff check above.

        ---

        ## Query parameters

        | Name | Type | Description |
        |---|---|---|
        | `cursor` | string | Position to read from. Comes from `next` or `previous`. |
        | `page_size` | integer | Rows per page. Defaults to 25, capped at 100. |

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "next": "http://localhost:8000/admin/users/?cursor=cD0yMDI2LTA5LTAx",
            "previous": null,
            "results": [
                {
                    "id": 42,
                    "email": "jane@example.com",
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "phone_number": "5551234567",
                    "is_active": true,
                    "is_verified": true,
                    "is_suspended": false,
                    "auth_provider": "email",
                    "date_joined": "2026-09-01T10:00:00Z",
                    "last_login": "2026-09-02T08:14:00Z"
                }
            ]
        }
        ```

        `next` is `null` on the last page. An empty database returns `results: []`,
        not a 404.

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

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```
        """

        return super().get(request, *args, **kwargs)
