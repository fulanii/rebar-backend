"""Google OAuth exchange shapes."""

from rest_framework import serializers

from authentication.serializers.user_info import UserInfoSerializer


class GoogleOAuthExchangeRequestSerializer(serializers.Serializer):
    code = serializers.CharField()


class GoogleOAuthExchangeResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    user_data = UserInfoSerializer()
