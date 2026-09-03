"""Guards on the generated OpenAPI schema."""

import pytest
from django.urls import get_resolver
from drf_spectacular.generators import SchemaGenerator

from .routes import OURS

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


@pytest.fixture(scope="module")
def schema():
    return SchemaGenerator().get_schema(request=None, public=True)


def test_schema_builds_without_warnings(capsys):
    SchemaGenerator().get_schema(request=None, public=True)

    warnings = [line for line in capsys.readouterr().err.splitlines() if "warning" in line.lower()]

    assert warnings == [], "drf-spectacular emitted warnings:\n" + "\n".join(warnings)


def test_every_endpoint_is_in_the_schema(schema):
    assert schema["paths"], "the schema contains no paths at all"

    for path in ("/auth/register/", "/auth/login/", "/auth/me/", "/token/refresh/"):
        assert path in schema["paths"], f"{path} is missing from the schema"


def test_every_view_method_has_a_docstring():
    undocumented = []

    for pattern in get_resolver().url_patterns:
        for sub in getattr(pattern, "url_patterns", [pattern]):
            view_class = getattr(sub.callback, "cls", None)
            if view_class is None:
                continue

            # Third-party views mounted in development (the Swagger pages) are not
            # ours to document.
            if not view_class.__module__.startswith(("administration", "authentication", "config")):
                continue

            for method in HTTP_METHODS:
                handler = getattr(view_class, method, None)
                if handler is not None and not (handler.__doc__ or "").strip():
                    undocumented.append(f"{view_class.__name__}.{method}")

    assert undocumented == [], "these view methods have no docstring: " + ", ".join(undocumented)


def routed_views_with_parameters():
    """Every view of ours, with the path parameter names the URLconf will hand it."""
    found = []

    def walk(patterns, converters):
        for pattern in patterns:
            names = converters | set(getattr(pattern.pattern, "converters", {}))
            nested = getattr(pattern, "url_patterns", None)

            if nested is not None:
                walk(nested, names)
                continue

            view_class = getattr(pattern.callback, "cls", None)

            if view_class is not None and view_class.__module__.startswith(OURS):
                found.append((view_class, names))

    walk(get_resolver().url_patterns, set())

    return found


def test_every_path_parameter_is_documented():
    """
    `{id}` alone does not say whose id. The name has to appear in the docstring.

    A caller reading "id" has to guess whether it means the user, the record the
    endpoint creates, or something else again, and the guess is only checkable by
    trying it against production data.
    """
    undocumented = []

    for view_class, parameters in routed_views_with_parameters():
        for method in HTTP_METHODS:
            handler = getattr(view_class, method, None)
            doc = (handler.__doc__ or "") if handler is not None else None

            if doc is None:
                continue

            for name in sorted(parameters):
                if "## Path parameters" not in doc or f"`{name}`" not in doc:
                    undocumented.append(f"{view_class.__name__}.{method}: {name}")

    assert undocumented == [], "document these in a `## Path parameters` table:\n" + "\n".join(undocumented)


def test_every_write_method_says_what_it_accepts():
    """A POST or PATCH docstring has to name its fields, or say it takes no body."""
    undocumented = []

    for view_class, _ in routed_views_with_parameters():
        for method in ("post", "put", "patch"):
            handler = getattr(view_class, method, None)
            doc = (handler.__doc__ or "") if handler is not None else None

            if doc is None:
                continue

            if not any(marker in doc for marker in ("## Body", "## Request Body", "no body")):
                undocumented.append(f"{view_class.__name__}.{method}")

    assert undocumented == [], "these need a `## Body` table, or a line saying they take no body:\n" + "\n".join(
        undocumented
    )
