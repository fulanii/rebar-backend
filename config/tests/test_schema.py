"""Guards on the generated OpenAPI schema."""

import pytest
from django.urls import get_resolver
from drf_spectacular.generators import SchemaGenerator

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
