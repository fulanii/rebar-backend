"""Permission classes, one per level of access this API hands out."""

from rest_framework.permissions import IsAdminUser


class IsSuperUser(IsAdminUser):
    """
    Staff, and a superuser on top.

    Subclasses `IsAdminUser` rather than replacing it, so the floor every route in this
    app stands on is the same one `config/tests/test_permissions.py` checks for, and a
    route can only ever be made stricter than that, never looser by accident.
    """

    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and request.user.is_superuser)
