"""
Guards on who can reach the administration API.

Every route in that app confirms whether an address is registered, which every route
under `auth/` is written to refuse. One view mounted without the staff check turns the
authentication app's non-disclosure into a formality, and nothing about the response
would look wrong.

The check is here rather than in the app because it has to hold for views nobody has
written yet, including in whatever app comes next.
"""

from rest_framework.permissions import IsAdminUser

from .routes import routed_views

GUARDED_APPS = ("administration",)


def guarded_views():
    """Every routed view belonging to an app that must not be reachable by a user."""
    return [view for view in routed_views() if view.__module__.startswith(GUARDED_APPS)]


def test_the_guarded_apps_actually_have_routes():
    """Otherwise the checks below pass by having nothing to check."""
    assert guarded_views() != [], f"no routed views found in {GUARDED_APPS}, has the URLconf changed?"


def test_every_administration_view_requires_staff():
    """
    `IsAdminUser`, or something built on it. `IsAuthenticated` is not enough here.

    A subclass counts, so a stricter check for a superuser-only route still passes,
    while a route that only asks for a signed-in account fails.
    """
    offenders = []

    for view in guarded_views():
        classes = getattr(view, "permission_classes", [])

        if not any(isinstance(klass, type) and issubclass(klass, IsAdminUser) for klass in classes):
            names = ", ".join(klass.__name__ for klass in classes) or "none"
            offenders.append(f"{view.__module__}.{view.__name__}: {names}")

    assert offenders == [], "these views do not require staff:\n" + "\n".join(offenders)
