"""Permission classes, one per level of access this API hands out."""

from rest_framework.permissions import SAFE_METHODS, IsAdminUser


class IsSuperUser(IsAdminUser):
    """
    Staff, and a superuser on top.

    Subclasses `IsAdminUser` rather than replacing it, so the floor every route in this
    app stands on is the same one `config/tests/test_permissions.py` checks for, and a
    route can only ever be made stricter than that, never looser by accident.
    """

    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and request.user.is_superuser)


class IsSuperUserToWrite(IsAdminUser):
    """
    Staff to read, a superuser for anything else.

    For a route whose read and write share one path. Built on `IsAdminUser` for the
    same reason as `IsSuperUser`: the floor is staff whatever the method.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return request.method in SAFE_METHODS or request.user.is_superuser
