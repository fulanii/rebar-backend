"""Login request and response shapes."""

from django.contrib.auth import authenticate
from rest_framework import serializers

from authentication.models import CustomUser

from .user_info import UserInfoSerializer


class UserLoginRequestSerializer(serializers.Serializer):
    """
    Checks an email and password and hands the view an authenticated user.

    A wrong password and an unknown address return the same message, so this cannot
    be used to discover which addresses are registered.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    default_error_messages = {
        "invalid_credentials": "Incorrect email or password.",
        "not_verified": "Please verify your email address before signing in.",
    }

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        password = attrs["password"]

        user = authenticate(request=self.context.get("request"), username=email, password=password)

        if user is None:
            user = CustomUser.objects.filter(email=email).first()

            if user is None or not user.check_password(password):
                self.fail("invalid_credentials")

        if not (user.is_active and user.is_verified):
            self.fail("not_verified")

        attrs["user"] = user
        return attrs


class UserLoginResponseSerializer(serializers.Serializer):
    """The refresh token is absent by design: it goes back as an httpOnly cookie."""

    access = serializers.CharField()
    user_data = UserInfoSerializer()
