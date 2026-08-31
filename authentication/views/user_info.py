from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.serializers import UserInfoSerializer
from authentication.throttles import UserInfoRateThrottle


@extend_schema(
    tags=["Authentication-Accounts"],
    summary="Get the signed-in user's profile",
    responses={200: UserInfoSerializer},
)
class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserInfoRateThrottle]

    def get(self, request):
        """
        The signed-in user's own profile.

        **Endpoint:** GET `auth/me/`

        **Authentication:** JWT required

        **Throttle:** 60/minute per user (`user_info` scope) -- clients call this on
        every page load to rehydrate their session.

        Read-only. There is no profile-update endpoint.

        ---

        ## Responses

        ### 200 OK
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
            "date_joined": "2026-08-29T10:00:00Z"
        }
        ```

        ### 401 Unauthorized
        Missing, malformed or expired access token:

        ```json
        {
            "detail": "Authentication credentials were not provided."
        }
        ```

        A suspended account, on its very next request after suspension:

        ```json
        {
            "detail": "Your account is suspended."
        }
        ```

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```
        """

        return Response(UserInfoSerializer(request.user).data, status=status.HTTP_200_OK)
