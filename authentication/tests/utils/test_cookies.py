"""
The refresh-token cookie.

Guardrail #3: set and delete must agree on name, path and domain, or logout clears a
cookie that does not exist and leaves the real session alive.
"""

import pytest
from rest_framework.response import Response

from authentication.utils import (
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
    delete_refresh_cookie,
    get_refresh_cookie,
    set_refresh_cookie,
)


@pytest.fixture
def response():
    return Response()


class TestSetting:
    def test_the_cookie_is_httponly(self, response):
        set_refresh_cookie(response, "a-token")

        assert response.cookies[REFRESH_COOKIE_NAME]["httponly"] is True

    def test_the_cookie_is_scoped_to_the_token_endpoints(self, response):
        set_refresh_cookie(response, "a-token")

        assert response.cookies[REFRESH_COOKIE_NAME]["path"] == REFRESH_COOKIE_PATH

    def test_the_path_covers_refresh_and_logout(self):
        """Too narrow a path and logout cannot read the cookie it needs to revoke."""
        assert "/token/refresh/".startswith(REFRESH_COOKIE_PATH)
        assert "/token/blacklist/".startswith(REFRESH_COOKIE_PATH)

    def test_samesite_is_lax(self, response):
        set_refresh_cookie(response, "a-token")

        assert response.cookies[REFRESH_COOKIE_NAME]["samesite"] == "Lax"

    def test_max_age_matches_the_refresh_token_lifetime(self, response, settings):
        set_refresh_cookie(response, "a-token")

        expected = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
        assert response.cookies[REFRESH_COOKIE_NAME]["max-age"] == expected

    def test_no_domain_in_debug(self, response, settings):
        """Browsers reject a Domain attribute on localhost; the cookie would vanish."""
        settings.DEBUG = True
        set_refresh_cookie(response, "a-token")

        assert response.cookies[REFRESH_COOKIE_NAME]["domain"] == ""

    def test_domain_is_dotted_when_deployed(self, response, settings):
        settings.DEBUG = False
        settings.DOMAIN = "example.com"
        set_refresh_cookie(response, "a-token")

        assert response.cookies[REFRESH_COOKIE_NAME]["domain"] == ".example.com"

    def test_secure_follows_the_session_cookie_setting(self, response, settings):
        settings.SESSION_COOKIE_SECURE = True
        set_refresh_cookie(response, "a-token")

        assert response.cookies[REFRESH_COOKIE_NAME]["secure"] is True


class TestDeleting:
    @pytest.mark.parametrize("debug", [True, False])
    def test_delete_matches_the_attributes_used_to_set(self, settings, debug):
        settings.DEBUG = debug
        settings.DOMAIN = "example.com"

        written = Response()
        set_refresh_cookie(written, "a-token")

        cleared = Response()
        delete_refresh_cookie(cleared)

        for attribute in ("path", "domain"):
            assert cleared.cookies[REFRESH_COOKIE_NAME][attribute] == written.cookies[REFRESH_COOKIE_NAME][attribute]

    def test_delete_empties_the_value(self):
        response = Response()
        delete_refresh_cookie(response)

        assert response.cookies[REFRESH_COOKIE_NAME].value == ""


class TestReading:
    def test_returns_the_cookie_value(self, rf):
        request = rf.post("/token/refresh/")
        request.COOKIES[REFRESH_COOKIE_NAME] = "a-token"

        assert get_refresh_cookie(request) == "a-token"

    def test_returns_none_when_absent(self, rf):
        assert get_refresh_cookie(rf.post("/token/refresh/")) is None
