"""Administration routes, mounted at `/admin/` in config/urls.py."""

from django.urls import path

from .views import UserDetailView, UserListView, UserUpdateView

urlpatterns = [
    path("users/", UserListView.as_view(), name="admin-user-list"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="admin-user-detail"),
    path("users/<int:pk>/update/", UserUpdateView.as_view(), name="admin-user-update"),
]
