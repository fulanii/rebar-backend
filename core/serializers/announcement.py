"""The banner as the public sees it."""

from rest_framework import serializers

from core.models import Announcement


class AnnouncementResponseSerializer(serializers.ModelSerializer):
    """The text and when it last changed. Never who wrote it."""

    class Meta:
        model = Announcement
        fields = ["message", "updated_at"]
        read_only_fields = fields
