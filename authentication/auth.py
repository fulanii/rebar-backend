"""The project's default authentication class."""

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class SuspensionAwareJWTAuthentication(JWTAuthentication):
    """JWT authentication that also refuses suspended accounts."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.is_suspended:
            raise AuthenticationFailed("Your account is suspended.", code="account_suspended")
        return user


class SuspensionAwareJWTScheme(SimpleJWTScheme):
    """Resolves the class above for drf-spectacular, which matches by exact class."""

    target_class = "authentication.auth.SuspensionAwareJWTAuthentication"
