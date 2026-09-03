"""Token endpoint shapes."""

from rest_framework import serializers


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
