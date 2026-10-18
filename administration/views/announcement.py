"""Editing the site-wide announcement banner."""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from administration.permissions import IsSuperUserToWrite
from administration.serializers import AnnouncementDetailResponseSerializer, AnnouncementRequestSerializer
from administration.throttles import AdminWriteRateThrottle
from core.models import Announcement

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["Administration-Announcement"],
    summary="Read, write or remove the site-wide banner",
    request=AnnouncementRequestSerializer,
    responses={
        200: AnnouncementDetailResponseSerializer,
        201: AnnouncementDetailResponseSerializer,
        204: None,
    },
)
class AnnouncementEditView(APIView):
    permission_classes = [IsSuperUserToWrite]
    throttle_classes = [AdminWriteRateThrottle]

    @extend_schema(
        summary="The banner as it stands, hidden or not, for the editor to load.",
    )
    def get(self, request):
        """
        The banner as it stands, hidden or not, for the editor to load.

        **Endpoint:** GET `admin/announcement/`

        **Authentication:** JWT required, and the account must be at least **staff**

        **Throttle:** 60/minute per account (`admin_write` scope, one budget for the
        whole editor)

        Unlike the public `announcement/`, a hidden banner is returned with its text,
        so it can be edited and shown again without retyping it.

        ---

        ## Responses

        ### 200 OK
        ```json
        {
            "message": "Scheduled maintenance Sunday 2-4am UTC.",
            "is_active": false,
            "updated_at": "2026-10-18T09:30:00Z",
            "updated_by": "root@example.com"
        }
        ```

        When no banner has been written the body is literally `null`. `updated_by` is
        `null` once the account that last edited it has been deleted.

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

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```
        """

        announcement = Announcement.current()
        data = AnnouncementDetailResponseSerializer(announcement).data if announcement else None

        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Write the banner, creating it the first time.",
    )
    def put(self, request):
        """
        Write the banner, creating it the first time.

        **Endpoint:** PUT `admin/announcement/`

        **Authentication:** JWT required, and the account must be a **superuser**

        **Throttle:** 60/minute per account (`admin_write` scope)

        There is only ever one banner, so this replaces it whole rather than adding
        another. Send both fields every time: `PUT` does not merge, and an omitted
        `is_active` means `true`. `updated_by` is the caller, never the body.

        To take the banner down but keep the text, send `is_active: false`. To remove
        it entirely, `DELETE`.

        ---

        ## Body

        | Field | Type | Required | Notes |
        |---|---|---|---|
        | `message` | string | Yes | At most 255 characters, trimmed. May be empty only when `is_active` is `false`. |
        | `is_active` | boolean | No | Whether the public endpoint shows it. Defaults to `true`. |

        ---

        ## Responses

        ### 201 Created
        The first banner. Same shape as GET.

        ### 200 OK
        The banner was replaced. Same shape as GET.

        ### 400 Bad Request
        ```json
        {
            "message": ["An active banner needs a message."]
        }
        ```

        ```json
        {
            "message": ["Ensure this field has no more than 255 characters."]
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

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```
        """

        serializer = AnnouncementRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        existed = Announcement.current() is not None
        announcement = Announcement(**serializer.validated_data, updated_by=request.user)
        announcement.save()

        logger.info(
            "event=announcement_written actor=%s active=%s created=%s",
            request.user.pk,
            announcement.is_active,
            not existed,
        )

        return Response(
            AnnouncementDetailResponseSerializer(announcement).data,
            status=status.HTTP_200_OK if existed else status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Remove the banner entirely.",
    )
    def delete(self, request):
        """
        Remove the banner entirely.

        **Endpoint:** DELETE `admin/announcement/`

        **Authentication:** JWT required, and the account must be a **superuser**

        **Throttle:** 60/minute per account (`admin_write` scope)

        Takes **no body**. Afterwards both GETs return `null` and the next `PUT` creates
        a fresh banner. To hide it but keep the text, `PUT` with `is_active: false`.

        ---

        ## Responses

        ### 204 No Content
        Removed. No body.

        ### 404 Not Found
        ```json
        {
            "detail": "There is no announcement to delete."
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

        ### 429 Too Many Requests
        ```json
        {
            "detail": "Request was throttled. Expected available in 30 seconds."
        }
        ```
        """

        deleted, _ = Announcement.objects.filter(pk=Announcement.SINGLETON_ID).delete()

        if not deleted:
            return Response({"detail": "There is no announcement to delete."}, status=status.HTTP_404_NOT_FOUND)

        logger.info("event=announcement_deleted actor=%s", request.user.pk)

        return Response(status=status.HTTP_204_NO_CONTENT)
