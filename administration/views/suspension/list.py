"""Every suspension ever issued, newest first."""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from administration.models import Suspension
from administration.pagination import SuspensionCursorPagination
from administration.permissions import IsSuperUser
from administration.serializers import SuspensionResponseSerializer
from administration.throttles import AdminReadRateThrottle


@extend_schema(
    tags=["Administration-Users"],
    summary="List every suspension",
    responses={200: SuspensionResponseSerializer(many=True)},
)
class SuspensionListView(ListAPIView):
    permission_classes = [IsSuperUser]
    throttle_classes = [AdminReadRateThrottle]
    pagination_class = SuspensionCursorPagination
    serializer_class = SuspensionResponseSerializer
    queryset = Suspension.objects.select_related("suspended_by", "lifted_by")

    def get(self, request, *args, **kwargs):
        """
        Every suspension on record, newest first.

        **Endpoint:** GET `admin/suspensions/`

        **Authentication:** JWT required, and the account must be a **superuser**

        **Throttle:** 120/minute per account (`admin_read` scope)

        The whole history, not the current state: an account suspended and reinstated
        three times appears three times, and a row with `lifted_at` set is a suspension
        that is over. Whether an account is suspended *right now* is `is_suspended` on
        `admin/users/{user_id}/`, and the open row here is the one with `lifted_at` null.

        Takes **no body and no path parameters**. There is no per-account variant of
        this route, and the `user` on each row is an account id, never a suspension id.

        Cursor paginated on `suspended_at`, for the same reason the user list is: new
        rows land at the front while a page is being read, and a page number would show
        one twice or skip it.

        ---

        ## Query parameters

        | Name | Type | Description |
        |---|---|---|
        | `cursor` | string | Position to read from. Comes from `next` or `previous`. |

        The cursor value is opaque: its format is not part of this contract, so follow
        `next` rather than building one.
        | `page_size` | integer | Rows per page. Defaults to 25, capped at 100. |

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "next": "http://localhost:8000/admin/suspensions/?cursor=cD0yMDI2LTA5LTAx",
            "previous": null,
            "results": [
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
            ]
        }
        ```

        `suspended_by` and `lifted_by` are the operator's email address, and either can
        be `null` when that account has since been deleted. `results` is `[]` when
        nobody has ever been suspended, not a 404.

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

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```
        """

        return super().get(request, *args, **kwargs)
