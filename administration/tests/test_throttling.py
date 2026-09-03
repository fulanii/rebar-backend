"""
Rate limits for this app.

Guardrail 2: a rate configured without a class does nothing at all, and a class whose
scope has no rate throttles nothing. The pair is pinned here so neither half can be
removed on its own.
"""

import pytest

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
