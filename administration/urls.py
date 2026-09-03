"""Administration routes, mounted at `/admin/` in config/urls.py."""

from django.urls import path

from .views import (
    SuspensionListView,
    SuspensionView,
    UserDeleteView,
    UserDetailView,
    UserListView,
    UserUpdateView,
)

urlpatterns = [
    path("users/", UserListView.as_view(), name="admin-user-list"),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="admin-user-detail"),
    path("users/<int:user_id>/update/", UserUpdateView.as_view(), name="admin-user-update"),
    path("users/<int:user_id>/suspension/", SuspensionView.as_view(), name="admin-user-suspension"),
    path("users/<int:user_id>/delete/", UserDeleteView.as_view(), name="admin-user-delete"),
    path("suspensions/", SuspensionListView.as_view(), name="admin-suspension-list"),
]
