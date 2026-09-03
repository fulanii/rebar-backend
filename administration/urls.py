"""Administration routes, mounted at `/admin/` in config/urls.py."""

from django.urls import path

from .views import UserListView

urlpatterns = [
    path("users/", UserListView.as_view(), name="admin-user-list"),
]
