"""Walking the project's routing table. Shared by the guards in this package."""

from django.urls import get_resolver

OURS = ("authentication", "config")


def routed_views(ours_only=True):
    """
    Every view class reachable through the URLconf, deduplicated.

    `ours_only` drops the third-party views mounted in development -- the Swagger
    pages and the admin -- which are not ours to document or rate limit.
    """
    seen = {}

    def walk(patterns):
        for pattern in patterns:
            nested = getattr(pattern, "url_patterns", None)

            if nested is not None:
                walk(nested)
                continue

            view_class = getattr(pattern.callback, "cls", None)

            if view_class is None:
                continue
            if ours_only and not view_class.__module__.startswith(OURS):
                continue

            seen[f"{view_class.__module__}.{view_class.__name__}"] = view_class

    walk(get_resolver().url_patterns)

    return list(seen.values())
