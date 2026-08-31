"""
Guards on the house style, where a violation is cheap to make and slow to notice.

Only rules worth a failing build live here -- the rest of docs/ai/conventions.md is
read by people and by assistants, not enforced.
"""

import ast
from pathlib import Path

from django.conf import settings

VIEW_PACKAGES = "*/views"


def view_modules():
    """Every view source file in the project, excluding package exports."""
    root = Path(settings.BASE_DIR)

    for package in root.glob(VIEW_PACKAGES):
        for path in sorted(package.rglob("*.py")):
            if path.name != "__init__.py":
                yield path.relative_to(root), path


def test_one_view_per_file():
    """
    A module with two views in it is a module to split -- see docs/ai/conventions.md.

    The rule exists so that a file's name tells you what is in it, and so two
    endpoints are never edited as one blob. `jwt_tokens.py` broke it once with three.
    """
    offenders = []

    for name, path in view_modules():
        classes = [
            node.name
            for node in ast.parse(path.read_text(encoding="utf-8")).body
            if isinstance(node, ast.ClassDef) and node.name.endswith("View")
        ]

        if len(classes) > 1:
            offenders.append(f"{name}: {', '.join(classes)}")

    assert offenders == [], "split these into one view per file:\n" + "\n".join(offenders)
