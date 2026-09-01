"""The project's default authentication class."""

from datetime import timezone as datetime_timezone

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class SuspensionAwareJWTAuthentication(JWTAuthentication):
    """
    JWT authentication that also refuses suspended accounts and stale tokens.

    A JWT is stateless, so without these checks a token stays good for its full
    lifetime no matter what happens to the account behind it. Both checks are free:
    SimpleJWT has already loaded the user row by this point.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        if user.is_suspended:
            raise AuthenticationFailed("Your account is suspended.", code="account_suspended")

        if self.issued_before_revocation(user, validated_token):
            raise AuthenticationFailed("Your session has ended. Please sign in again.", code="session_revoked")

        return user

    def issued_before_revocation(self, user, validated_token):
        """
        True when the token was issued before the account's sessions were revoked.

        Blacklisting handles refresh tokens, which are stored. Access tokens are not
        stored anywhere, so this timestamp is the only way to stop one, without it a
        password reset leaves the intruder a 30-minute tail.

        `iat` is whole seconds, so the comparison is inclusive: a token minted in the
        same second as the revocation is refused. The cost is a fresh sign-in within
        that one second being asked to sign in again; the alternative is letting a
        token from that second through.
        """
        if user.sessions_revoked_at is None:
            return False

        issued_at = validated_token.payload.get("iat")

        if issued_at is None:
            return True

        return issued_at <= int(user.sessions_revoked_at.astimezone(datetime_timezone.utc).timestamp())


class SuspensionAwareJWTScheme(SimpleJWTScheme):
    """Resolves the class above for drf-spectacular, which matches by exact class."""

    target_class = "authentication.auth.SuspensionAwareJWTAuthentication"
