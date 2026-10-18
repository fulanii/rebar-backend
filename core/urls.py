"""Core routes, mounted at the root in config/urls.py."""

from django.urls import path

from .views import AnnouncementView

urlpatterns = [
    path("announcement/", AnnouncementView.as_view(), name="announcement"),
]
