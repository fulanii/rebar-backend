"""Deleting one account, permanently."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from administration.permissions import IsSuperUser
from administration.serializers import UserDeleteResponseSerializer
from administration.throttles import AdminWriteRateThrottle
from authentication.models import CustomUser


@extend_schema(
    tags=["Administration-Users"],
    summary="Delete one user account permanently",
    request=None,
    responses={200: UserDeleteResponseSerializer},
)
class UserDeleteView(GenericAPIView):
    permission_classes = [IsSuperUser]
    throttle_classes = [AdminWriteRateThrottle]
    serializer_class = UserDeleteResponseSerializer
    queryset = CustomUser.objects.all()
    lookup_url_kwarg = "user_id"

    def delete(self, request, *args, **kwargs):
        """
        Delete an account and everything hanging off it. There is no undo.

        **Endpoint:** DELETE `admin/users/{user_id}/delete/`

        **Authentication:** JWT required, and the account must be a **superuser**

        **Throttle:** 60/minute per account (`admin_write` scope)

        A hard delete: the row is gone, and so is everything with a cascade onto it.
        That includes the account's **suspension history**, so an account deleted after
        a fraud investigation takes the record of that investigation with it, and its
        outstanding refresh tokens, which is what signs it out everywhere.

        Suspensions this account *issued* survive, with `suspended_by` set to `null`.
        The record of what somebody did outlives their account on purpose.

        Reach for `admin/users/{user_id}/suspension/` for anything short of an erasure
        request. Suspension locks the account out immediately, keeps the evidence, and
        can be undone; this cannot. If you need the account gone but the record kept,
        `docs/ai/recipes/soft-delete-accounts.md` covers what changes.

        Takes **no body and no query parameters**. Read
        `admin/users/{user_id}/` first and check the address on it: the id in the path
        is the only thing naming what gets destroyed, and one digit wrong is a
        different person.

        You cannot delete the account you are signed in as.

        ---

        ## Path parameters

        | Name | Type | Description |
        |---|---|---|
        | `user_id` | integer | The **account being deleted**, as `id` from `admin/users/`. |

        Never the id of the superuser making the call, which this endpoint refuses.

        ---

        ## Responses

        ### 200 OK
        A receipt, because the account can no longer be looked up to see what went:

        ```json
        {
            "id": 42,
            "email": "jane@example.com",
            "suspensions_deleted": 2
        }
        ```

        ### 400 Bad Request
        Deleting the account you are signed in as:

        ```json
        {
            "detail": "You cannot delete your own account."
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
        No account with that id, including one deleted a moment ago. A repeated call
        answers 404, not 200:

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

        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        receipt = {
            "id": user.pk,
            "email": user.email,
            "suspensions_deleted": user.suspensions.count(),
        }
        user.delete()

        return Response(UserDeleteResponseSerializer(receipt).data, status=status.HTTP_200_OK)
