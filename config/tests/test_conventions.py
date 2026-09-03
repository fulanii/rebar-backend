"""
Guards on the house style, where a violation is cheap to make and slow to notice.

Only rules worth a failing build live here, the rest of docs/ai/conventions.md is
read by people and by assistants, not enforced.
"""

import ast
from pathlib import Path

from django.conf import settings

VIEW_PACKAGES = "*/views"
SKIPPED_DIRECTORIES = {"__pycache__", "migrations", ".venv", "venv", "env"}
FUNCTION_BODY_LIMIT = 50
CLASS_BODY_LIMIT = 70


def view_modules():
    """Every view source file in the project, excluding package exports."""
    root = Path(settings.BASE_DIR)

    for package in root.glob(VIEW_PACKAGES):
        for path in sorted(package.rglob("*.py")):
            if path.name != "__init__.py":
                yield path.relative_to(root), path


def test_one_view_per_file():
    """
    A module with two views in it is a module to split, see docs/ai/conventions.md.

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


def project_modules():
    """Every source file in the project, migrations and vendored trees aside."""
    root = Path(settings.BASE_DIR)

    for path in sorted(root.rglob("*.py")):
        parts = path.relative_to(root).parts

        if any(part in SKIPPED_DIRECTORIES for part in parts):
            continue

        yield path.relative_to(root), path


def docstring_lines(tree):
    """Line spans of every docstring in a module, which do not count towards length."""
    spans = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None

            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                spans.append(range(first.lineno, first.end_lineno + 1))

    return spans


def body_length(node, lines, spans):
    """Lines of actual code in a definition, blank lines and docstrings excluded."""
    body = [child for child in node.body if not any(child.lineno in span for span in spans)]

    if not body:
        return 0

    covered = range(body[0].lineno, body[-1].end_lineno + 1)

    return sum(1 for number in covered if lines[number - 1].strip() and not any(number in span for span in spans))


def definitions(kinds):
    """Every definition of the given node kinds, with its measured body length."""
    for name, path in project_modules():
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)
        spans = docstring_lines(tree)

        for node in ast.walk(tree):
            if isinstance(node, kinds):
                yield f"{name}:{node.lineno} {node.name}", body_length(node, lines, spans)


def test_functions_stay_short():
    """
    A function past FUNCTION_BODY_LIMIT lines of code is doing more than one thing.

    Docstrings do not count, so the house API docstring on a view method is free.
    The limit is on what the reader has to hold in their head, see
    docs/ai/conventions.md.
    """
    offenders = [
        f"{where}: {length} lines"
        for where, length in definitions((ast.FunctionDef, ast.AsyncFunctionDef))
        if length > FUNCTION_BODY_LIMIT
    ]

    assert offenders == [], f"extract a helper, these are over {FUNCTION_BODY_LIMIT} lines:\n" + "\n".join(offenders)


def test_classes_stay_short():
    """
    A class past CLASS_BODY_LIMIT lines of code has more than one responsibility.

    Test classes are exempt: they group cases rather than model anything, and a long
    one means thorough coverage.
    """
    offenders = [
        f"{where}: {length} lines"
        for where, length in definitions((ast.ClassDef,))
        if length > CLASS_BODY_LIMIT and "test" not in where.split(":")[0]
    ]

    assert offenders == [], f"split these, they are over {CLASS_BODY_LIMIT} lines:\n" + "\n".join(offenders)


def test_imports_follow_the_house_rules():
    """
    One dot for the same folder, the full path from the app for anything else.

    `..` and `...` are banned outright, see docs/ai/conventions.md. Counting dots
    against a tree four levels deep is how a file ends up importing from the wrong
    place, and every dot has to be recounted when a file moves.
    """
    offenders = []

    for name, path in project_modules():
        package = ".".join(name.parts[:-1])

        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ImportFrom):
                continue

            if node.level > 1:
                offenders.append(f"{name}:{node.lineno} `from {'.' * node.level}` — use the full path from the app")

            elif node.level == 0 and node.module and node.module.startswith(f"{package}."):
                if "." not in node.module[len(package) + 1 :]:
                    offenders.append(f"{name}:{node.lineno} `from {node.module}` — same folder, use one dot")

    assert offenders == [], "fix these imports:\n" + "\n".join(offenders)
