"""
Guards on the routing table itself.

Every check here asks the same question: is something reachable over HTTP without the
protection the rest of the project assumes it has? Walking the URLconf rather than a
list of views is the point -- a view is dangerous when it is *routed*, and a list can
be forgotten.
"""

from .routes import routed_views


def test_every_routed_view_declares_a_throttle():
    """
    `DEFAULT_THROTTLE_CLASSES` is empty on purpose -- each view states its own limit,
    per docs/ai/conventions.md. The cost of that choice is that a view which forgets
    `throttle_classes` is not rate limited at all: it fails open, silently, with
    nothing in the logs. This is the check that catches it.

    `GoogleOAuthCallbackView` shipped that way once. See guardrail 2.
    """
    unthrottled = [view.__name__ for view in routed_views() if not view().get_throttles()]

    assert unthrottled == [], "these routed views are not rate limited at all"


def test_every_routed_view_declares_its_permissions():
    """
    Guardrail: `permission_classes` is always explicit, even when it matches the
    default, so who may call an endpoint never takes a search to establish.
    """
    implicit = [view.__name__ for view in routed_views() if "permission_classes" not in vars(view)]

    assert implicit == [], "these routed views do not set permission_classes explicitly"
