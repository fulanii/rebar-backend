"""The token endpoints and the refresh-cookie contract."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from authentication.utils import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH

pytestmark = pytest.mark.django_db


def login(client, user, password):
    """Sign in and leave the refresh cookie on the client, as a browser would."""
    return client.post(reverse("login"), {"email": user.email, "password": password}, format="json")


class TestConcurrentRefresh:
    """
    Two tabs refreshing at once, both holding the cookie the browser shares between
    them. Rotation means exactly one of them can win, so the question is what the
    loser does to the session.

    Nothing. The loser gets a single 401 and the winner's token stays good. There is
    no grace window and no reuse-detection cascade: a blacklisted token is refused on
    its own, it does not take the session with it.
    """

    def test_the_first_request_wins(self, api_client, base_user, user_password):
        original = login(api_client, base_user, user_password).cookies[REFRESH_COOKIE_NAME].value

        api_client.cookies[REFRESH_COOKIE_NAME] = original
        winner = api_client.post(reverse("token_refresh"), {}, format="json")

        assert winner.status_code == 200
        assert winner.cookies[REFRESH_COOKIE_NAME].value != original

    def test_the_second_request_is_refused(self, api_client, base_user, user_password):
        original = login(api_client, base_user, user_password).cookies[REFRESH_COOKIE_NAME].value

        api_client.cookies[REFRESH_COOKIE_NAME] = original
        api_client.post(reverse("token_refresh"), {}, format="json")

        loser = APIClient()
        loser.cookies[REFRESH_COOKIE_NAME] = original
        response = loser.post(reverse("token_refresh"), {}, format="json")

        assert response.status_code == 401
        assert response.data["code"] == "token_not_valid"

    def test_the_loser_does_not_overwrite_the_cookie(self, api_client, base_user, user_password):
        """
        The 401 must carry no Set-Cookie, or the browser would replace the token the
        winning tab just stored with nothing, and both tabs would be signed out.
        """
        original = login(api_client, base_user, user_password).cookies[REFRESH_COOKIE_NAME].value
        api_client.cookies[REFRESH_COOKIE_NAME] = original
        api_client.post(reverse("token_refresh"), {}, format="json")

        loser = APIClient()
        loser.cookies[REFRESH_COOKIE_NAME] = original
        response = loser.post(reverse("token_refresh"), {}, format="json")

        assert REFRESH_COOKIE_NAME not in response.cookies

    def test_the_session_survives_the_collision(self, api_client, base_user, user_password):
        original = login(api_client, base_user, user_password).cookies[REFRESH_COOKIE_NAME].value

        api_client.cookies[REFRESH_COOKIE_NAME] = original
        rotated = api_client.post(reverse("token_refresh"), {}, format="json")
        rotated_token = rotated.cookies[REFRESH_COOKIE_NAME].value

        loser = APIClient()
        loser.cookies[REFRESH_COOKIE_NAME] = original
        loser.post(reverse("token_refresh"), {}, format="json")

        survivor = APIClient()
        survivor.cookies[REFRESH_COOKIE_NAME] = rotated_token
        assert survivor.post(reverse("token_refresh"), {}, format="json").status_code == 200

    def test_a_losing_refresh_revokes_no_other_session(self, api_client, base_user, user_password):
        """A replayed token is refused, not treated as a breach worth ending everything."""
        original = login(api_client, base_user, user_password).cookies[REFRESH_COOKIE_NAME].value
        api_client.cookies[REFRESH_COOKIE_NAME] = original
        api_client.post(reverse("token_refresh"), {}, format="json")

        loser = APIClient()
        loser.cookies[REFRESH_COOKIE_NAME] = original
        loser.post(reverse("token_refresh"), {}, format="json")

        base_user.refresh_from_db()
        assert base_user.sessions_revoked_at is None


class TestTokenRefresh:
    def test_refreshes_from_the_cookie_with_no_body(self, api_client, base_user, user_password):
        login(api_client, base_user, user_password)

        response = api_client.post(reverse("token_refresh"), {}, format="json")

        assert response.status_code == 200
        assert response.data["access"]

    def test_rotates_the_refresh_token(self, api_client, base_user, user_password):
        login_response = login(api_client, base_user, user_password)
        original = login_response.cookies[REFRESH_COOKIE_NAME].value

        response = api_client.post(reverse("token_refresh"), {}, format="json")
        rotated = response.cookies[REFRESH_COOKIE_NAME].value

        assert rotated != original

    def test_the_replaced_token_stops_working(self, api_client, base_user, user_password):
        login_response = login(api_client, base_user, user_password)
        original = login_response.cookies[REFRESH_COOKIE_NAME].value

        api_client.post(reverse("token_refresh"), {}, format="json")

        replay = APIClient()
        replay.cookies[REFRESH_COOKIE_NAME] = original
        assert replay.post(reverse("token_refresh"), {}, format="json").status_code == 401

    def test_missing_cookie_is_a_401_not_a_500(self, api_client):
        response = api_client.post(reverse("token_refresh"), {}, format="json")

        assert response.status_code == 401
        assert "detail" in response.data

    def test_a_garbage_cookie_is_rejected(self, api_client):
        api_client.cookies[REFRESH_COOKIE_NAME] = "not-a-token"

        response = api_client.post(reverse("token_refresh"), {}, format="json")

        assert response.status_code == 401


class TestTokenBlacklist:
    def test_logout_clears_the_cookie(self, api_client, base_user, user_password):
        login(api_client, base_user, user_password)

        response = api_client.post(reverse("token_blacklist"), {}, format="json")

        assert response.status_code == 205
        assert response.cookies[REFRESH_COOKIE_NAME].value == ""

    def test_the_deleted_cookie_matches_the_path_it_was_set_with(self, api_client, base_user, user_password):
        login(api_client, base_user, user_password)

        response = api_client.post(reverse("token_blacklist"), {}, format="json")

        assert response.cookies[REFRESH_COOKIE_NAME]["path"] == REFRESH_COOKIE_PATH

    def test_the_token_cannot_be_used_after_logout(self, api_client, base_user, user_password):
        login(api_client, base_user, user_password)
        stolen = api_client.cookies[REFRESH_COOKIE_NAME].value

        api_client.post(reverse("token_blacklist"), {}, format="json")

        attacker = APIClient()
        attacker.cookies[REFRESH_COOKIE_NAME] = stolen
        assert attacker.post(reverse("token_refresh"), {}, format="json").status_code == 401

    def test_logout_without_a_cookie_still_succeeds(self, api_client):
        response = api_client.post(reverse("token_blacklist"), {}, format="json")

        assert response.status_code == 205
