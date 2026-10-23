"""The admin overview: how many accounts, and how many are new."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from administration.serializers import StatsResponseSerializer
from administration.throttles import AdminReadRateThrottle
from administration.utils import account_stats


@extend_schema(
    tags=["Administration-Stats"],
    summary="Overview figures for the admin dashboard",
    responses={200: StatsResponseSerializer},
)
class StatsView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminReadRateThrottle]

    def get(self, request):
        """
        Overview figures for the admin dashboard.

        **Endpoint:** GET `admin/stats/`

        **Authentication:** JWT required, and the account must be staff

        **Throttle:** 120/minute per account (`admin_read` scope)

        Counted live on every request, in one query. Every account counts, verified or
        not, staff included: the same accounts `admin/users/` lists with no filters.

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "total_users": 312,
            "signups_last_7_days": 14
        }
        ```

        - `total_users`: every account.
        - `signups_last_7_days`: accounts created in the last seven days, rolling back
          from now rather than from the start of a calendar day.

        ### 401 Unauthorized
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

        return Response(StatsResponseSerializer(account_stats()).data, status=status.HTTP_200_OK)
