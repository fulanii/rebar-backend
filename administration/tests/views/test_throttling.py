"""
Rate limits for this app.

Guardrail 2: a rate configured without a class does nothing at all, and a class whose
scope has no rate throttles nothing. The pair is pinned here so neither half can be
removed on its own.
"""

import pytest
from django.urls import reverse

from administration import throttles

RATES = {
    "admin_read": "120/minute",
}


class TestConfiguredRates:
    @pytest.mark.parametrize("scope,expected", RATES.items())
    def test_the_documented_rate_is_configured(self, settings, scope, expected):
        assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][scope] == expected

    def test_every_scope_has_a_throttle_class(self):
        ours = [c for c in vars(throttles).values() if isinstance(c, type) and c.__module__ == throttles.__name__]
        used = {c.scope for c in ours}

        assert set(RATES) == used, "a rate without a class does nothing, and vice versa"


@pytest.mark.django_db
class TestTheUserListIsThrottled:
    def test_one_request_past_the_limit_is_refused(self, admin_client, settings):
        """
        Reads the limit from settings, so raising the rate does not slip past silently.

        The scope is per account, not per IP: operators share an office address, and an
        IP-keyed limit there would throttle the team rather than a runaway script.
        """
        url = reverse("admin-user-list")
        limit = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["admin_read"].split("/")[0])

        for _ in range(limit):
            admin_client.get(url)

        assert admin_client.get(url).status_code == 429
