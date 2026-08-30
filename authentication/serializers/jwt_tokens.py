"""Token endpoint shapes."""

from rest_framework import serializers


class TokenObtainPairResponseSerializer(serializers.Serializer):
    access = serializers.CharField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
