"""The announcement banner, read by every page of the site."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Announcement
from core.serializers import AnnouncementResponseSerializer
from core.throttles import AnnouncementRateThrottle


@extend_schema(
    tags=["Core-Announcement"],
    summary="The banner to show across the site",
    responses={200: AnnouncementResponseSerializer},
)
class AnnouncementView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AnnouncementRateThrottle]

    def get(self, request):
        """
        The active announcement banner, or `null` when there is nothing to show.

        **Endpoint:** GET `announcement/`

        **Authentication:** None. Any `Authorization` header is ignored, so a stale
        token never stops the banner loading, including on the sign-in page.

        **Throttle:** 120/minute per IP (`core_announcement` scope)

        A hidden banner reads exactly like no banner. Who wrote it is never included;
        operators edit it at `admin/announcement/`.

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "message": "Scheduled maintenance Sunday 2-4am UTC.",
            "updated_at": "2026-10-18T09:30:00Z"
        }
        ```

        When there is no banner, or it is hidden, the body is literally `null`.

        `updated_at` changes on every edit, so a client that lets people dismiss the
        banner can key the dismissal on it and show a changed banner again.

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```
        """

        announcement = Announcement.objects.filter(pk=Announcement.SINGLETON_ID, is_active=True).first()
        data = AnnouncementResponseSerializer(announcement).data if announcement else None

        return Response(data, status=status.HTTP_200_OK)
