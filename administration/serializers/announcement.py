"""Writing the site-wide banner, and the record an operator reads back."""

from rest_framework import serializers

from core.models import Announcement


class AnnouncementRequestSerializer(serializers.ModelSerializer):
    """The whole banner, every time. `PUT` replaces it rather than merging."""

    class Meta:
        model = Announcement
        fields = ["message", "is_active"]
        extra_kwargs = {"message": {"required": True}}

    def validate(self, attrs):
        if attrs.get("is_active", True) and not attrs["message"]:
            raise serializers.ValidationError({"message": ["An active banner needs a message."]})

        return attrs


class AnnouncementDetailResponseSerializer(serializers.ModelSerializer):
    """The banner as an operator sees it: hidden or not, and who last changed it."""

    updated_by = serializers.EmailField(source="updated_by.email", read_only=True, allow_null=True)

    class Meta:
        model = Announcement
        fields = ["message", "is_active", "updated_at", "updated_by"]
        read_only_fields = fields
