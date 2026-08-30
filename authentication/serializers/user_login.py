"""Login request and response shapes."""

from django.contrib.auth import authenticate
from rest_framework import serializers

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

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=attrs["password"],
        )

        if user is None:
            from authentication.models import CustomUser

            pending = CustomUser.objects.filter(email=email, is_active=False).first()
            if pending is not None and pending.check_password(attrs["password"]):
                self.fail("not_verified")

            self.fail("invalid_credentials")

        attrs["user"] = user
        return attrs


class UserLoginResponseSerializer(serializers.Serializer):
    """The refresh token is absent by design: it goes back as an httpOnly cookie."""

    access = serializers.CharField()
    user_data = UserInfoSerializer()
