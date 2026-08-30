"""Response shapes shared across features."""

from rest_framework import serializers


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
