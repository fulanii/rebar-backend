"""
Guards on the throttle configuration, across every app at once.

Each app pins its own rates in its own tests. What no app can see from the inside is
the whole table: a scope in settings that belongs to nobody, or a class whose scope was
never given a rate. Both fail open, silently, so they are checked here.

Apps are discovered, not listed. A new app with a `throttles.py` is covered the day it
is added, with nothing to remember.
"""

import importlib

import pytest
from django.apps import apps
from django.conf import settings

THIRD_PARTY = ("django.", "rest_framework")


def throttle_modules():
    """Every app's `throttles.py`, ours only, skipping apps that have none."""
    for config in apps.get_app_configs():
        if config.name.startswith(THIRD_PARTY):
            continue

        try:
            yield importlib.import_module(f"{config.name}.throttles")
        except ModuleNotFoundError:
            continue


def throttle_classes():
    """Every throttle class the project defines, paired with the app that owns it."""
    for module in throttle_modules():
        for value in vars(module).values():
            if isinstance(value, type) and value.__module__ == module.__name__:
                yield module.__name__, value


@pytest.fixture(scope="module")
def declared():
    return set(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])


@pytest.fixture(scope="module")
def defined():
    return list(throttle_classes())


def test_every_rate_belongs_to_a_class(declared, defined):
    """A rate nothing claims throttles nothing, and reads as protection that is not there."""
    orphans = declared - {klass.scope for _, klass in defined}

    assert orphans == set(), f"these rates have no throttle class in any app: {sorted(orphans)}"


def test_every_class_has_a_rate(declared, defined):
    """A scope with no rate is not a limit, DRF lets every request through."""
    missing = [f"{module}.{klass.__name__} ({klass.scope})" for module, klass in defined if klass.scope not in declared]

    assert missing == [], "these classes have a scope with no rate in settings:\n" + "\n".join(missing)


def test_no_scope_is_claimed_twice(defined):
    """
    Two classes on one scope keep separate counters, so the real limit is doubled.

    Sharing a scope on purpose is fine within one app's own rate, what this catches is
    a second app reusing a name that was already taken.
    """
    owners = {}

    for module, klass in defined:
        owners.setdefault(klass.scope, []).append(f"{module}.{klass.__name__}")

    shared = {scope: names for scope, names in owners.items() if len(names) > 1}

    assert shared == {}, f"one scope, more than one class, so the limit doubles: {shared}"
