"""
The refresh-token cookie.

Every endpoint that issues, refreshes or revokes a session goes through here. The
name, path and domain must match between setting and deleting the cookie.
"""

from django.conf import settings

REFRESH_COOKIE_NAME = "refresh"
REFRESH_COOKIE_PATH = "/token/"


def _refresh_cookie_domain():
    return None if settings.DEBUG else f".{settings.DOMAIN}"


def set_refresh_cookie(response, refresh):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
        domain=_refresh_cookie_domain(),
    )


def get_refresh_cookie(request):
    return request.COOKIES.get(REFRESH_COOKIE_NAME)


def delete_refresh_cookie(response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        domain=_refresh_cookie_domain(),
    )
