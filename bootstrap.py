#!/usr/bin/env python3
"""
Turn this boilerplate into your project.

    python bootstrap.py my_project

Creates .env, .env.staging and .env.prod with fresh secret keys, clears the
boilerplate's migrations, sets the API documentation title, and starts a new git
repository. Run it once, immediately after cloning.

Standard library only, so it runs before you have installed anything.
"""

import argparse
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = ROOT / ".bootstrapped"


def fail(message):
    print(f"\n  error: {message}\n", file=sys.stderr)
    sys.exit(1)


def title_from(name):
    return name.replace("_", " ").replace("-", " ").title()


def rewrite_titles(name):
    """Put the project's name on the API docs and the readme heading."""
    title = title_from(name)

    settings_base = ROOT / "config" / "settings" / "base.py"
    if settings_base.exists():
        text = settings_base.read_text(encoding="utf-8")
        text = text.replace('"TITLE": "SaaS Boilerplate API"', f'"TITLE": "{title} API"')
        settings_base.write_text(text, encoding="utf-8")

    readme = ROOT / "readme.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        text = text.replace("# SaaS Boilerplate — Backend", f"# {title} — Backend", 1)
        readme.write_text(text, encoding="utf-8")


def write_env_files():
    """
    Create .env, .env.staging and .env.prod from their .example files.

    Each gets its own generated SECRET_KEY, so a leaked development key cannot forge
    production sessions. Only .env is ever loaded; the other two are yours to fill in
    and copy from. Existing files are never overwritten.
    """
    written = []

    for example_name, target_name in (
        (".env.example", ".env"),
        (".env.staging.example", ".env.staging"),
        (".env.prod.example", ".env.prod"),
    ):
        example = ROOT / example_name
        target = ROOT / target_name

        if target.exists():
            print(f"  {target_name} already exists, leaving it alone")
            continue

        if not example.exists():
            print(f"  warning: {example_name} is missing, skipping")
            continue

        text = example.read_text(encoding="utf-8")
        text = text.replace("SECRET_KEY=", f"SECRET_KEY={secrets.token_urlsafe(50)}", 1)
        target.write_text(text, encoding="utf-8")
        written.append(target_name)

    return written


def clear_migrations():
    """Delete the boilerplate's migrations so your project starts with a clean history."""
    removed = 0
    for path in ROOT.rglob("migrations/*.py"):
        if path.name == "__init__.py":
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        path.unlink()
        removed += 1
    return removed


def reset_git():
    """Replace the boilerplate's history so your first commit is your own."""
    git_dir = ROOT / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    try:
        subprocess.run(["git", "init", "-q"], cwd=ROOT, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  warning: could not run `git init` -- run it yourself")
        return False


def main():
    parser = argparse.ArgumentParser(description="Turn this boilerplate into your project.")
    parser.add_argument("name", help="your project name, e.g. my_project")
    args = parser.parse_args()

    if MARKER.exists():
        fail("this project has already been bootstrapped.\n  Delete .bootstrapped to force it.")

    print(f"\n  Setting up '{args.name}'\n")

    written = write_env_files()
    if written:
        print(f"  wrote {', '.join(written)}, each with its own fresh SECRET_KEY")

    removed = clear_migrations()
    print(f"  cleared {removed} boilerplate migration file(s)")

    rewrite_titles(args.name)
    print(f"  set the API documentation title to '{title_from(args.name)} API'")

    if reset_git():
        print("  replaced the boilerplate's git history with a fresh repository")

    MARKER.write_text(f"{args.name}\n", encoding="utf-8")

    print("""
  Done. Next:

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt
    python manage.py makemigrations
    python manage.py migrate
    python manage.py runserver

  Then open http://localhost:8000/docs/

  .env is the only file the app loads. .env.staging and .env.prod are yours to
  fill in and copy from -- switch environment by changing DJANGO_SETTINGS_MODULE
  inside .env, or set the values in your host's dashboard.

  Configuration:  docs/configuration.md
  Deployment:     docs/deployment.md
  Before your first change: docs/ai/guardrails.md
""")


if __name__ == "__main__":
    main()
