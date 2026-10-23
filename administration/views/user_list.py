"""Every account in the system, for support and operations."""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser

from administration.pagination import UserPageNumberPagination
from administration.serializers import UserListQueryRequestSerializer, UserListQueryResponseSerializer
from administration.throttles import AdminReadRateThrottle
from administration.utils import filtered_users


@extend_schema(
    tags=["Administration-Users"],
    summary="List, filter, search and sort user accounts",
    parameters=[UserListQueryRequestSerializer],
    responses={200: UserListQueryResponseSerializer(many=True)},
)
class UserListView(ListAPIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminReadRateThrottle]
    pagination_class = UserPageNumberPagination
    serializer_class = UserListQueryResponseSerializer

    def get_queryset(self):
        return filtered_users(self.request.query_params)

    def get(self, request, *args, **kwargs):
        """
        Every account, or the ones matching the filters sent, newest signup first.

        **Endpoint:** GET `admin/users/`

        **Authentication:** JWT required, and the account must be staff

        **Throttle:** 120/minute per account (`admin_read` scope)

        Every filter is optional and only applies when sent; send several and an account
        has to match all of them. An invalid value is a 400 naming the parameter, never
        the whole table returned as if it were the filtered result.

        Page numbered, with `count` for the total. A signup landing while someone pages
        through shifts the rows down by one, so the next page can repeat the last row of
        the previous one. Ties in the sort are broken by `id`, so the order is otherwise
        stable from one page to the next.

        Deliberately reveals whether an address is registered, which the endpoints under
        `auth/` refuse to do. That is the point of this one, and it is why the route is
        useless without the staff check above.

        ---

        ## Query parameters

        | Name | Type | Description |
        |---|---|---|
        | `search` | string | Each word must appear in the email, first or last name. Case-insensitive. |
        | `phone` | string | Digits found anywhere in the stored `+…` number. Spaces, dashes and `+` are ignored. |
        | `has_phone` | boolean | Whether the account has a phone number at all. |
        | `is_active` | boolean | |
        | `is_verified` | boolean | Whether the email address is verified. |
        | `is_suspended` | boolean | |
        | `is_staff` | boolean | |
        | `auth_provider` | string | `email` or `google`. |
        | `has_logged_in` | boolean | `false` finds accounts that have never signed in. |
        | `joined_after` | date | `YYYY-MM-DD`, inclusive. |
        | `joined_before` | date | `YYYY-MM-DD`, inclusive. |
        | `timezone` | string | Which zone the `joined_*` days are counted in, e.g. `Europe/Paris`. Defaults to `UTC`. |
        | `ordering` | string | A field below, `-` in front for descending. Defaults to `-date_joined`. |
        | `page` | integer | Defaults to 1. |
        | `page_size` | integer | Rows per page. Defaults to 25, capped at 100. |

        Booleans take `true` or `false`. `ordering` takes `date_joined`, `last_login`,
        `email`, `first_name` or `last_name`; accounts that never signed in sort last by
        `last_login` in either direction.

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "count": 312,
            "next": "http://localhost:8000/admin/users/?auth_provider=email&page=2",
            "previous": null,
            "results": [
                {
                    "id": 42,
                    "email": "jane@example.com",
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "phone_number": "+12015550123",
                    "is_active": true,
                    "is_verified": true,
                    "is_phone_verified": false,
                    "is_suspended": false,
                    "auth_provider": "email",
                    "date_joined": "2026-09-01T10:00:00Z",
                    "last_login": "2026-09-02T08:14:00Z",
                    "is_staff": false,
                    "is_superuser": false
                }
            ]
        }
        ```

        `next` and `previous` carry the filters along, so follow them as they are. No
        match is `count: 0` and `results: []`, not a 404.

        ### 400 Bad Request
        One entry per invalid parameter:

        ```json
        {
            "ordering": ["\\"password\\" is not a valid choice."],
            "timezone": ["\\"Mars/Base\\" is not a known time zone, e.g. \\"Europe/Paris\\"."],
            "joined_before": ["Must be on or after joined_after."]
        }
        ```

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
        A `page` past the last one, or not a number:

        ```json
        {
            "detail": "Invalid page."
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
