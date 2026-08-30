#!/usr/bin/env python3
"""
Turn this boilerplate into your project.

    python bootstrap.py my_project

Creates .env, .env.staging and .env.prod with fresh secret keys and removes the
.example templates they replace, clears the boilerplate's migrations, sets the API
documentation title, gitignores the boilerplate's docs, starts a new git repository,
renames the project folder to your project name, and deletes itself.

Run it once, immediately after cloning.

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
    Create .env, .env.staging and .env.prod from their .example templates.

    Each gets its own generated SECRET_KEY, so a leaked development key cannot forge
    production sessions. Only .env is ever loaded; the other two are yours to fill in
    and copy from.

    Each template is deleted once its real file exists -- the real file carries the
    same variables, so keeping the template around would leave two nearly identical
    files and an obvious way to edit the wrong one. Existing files are never
    overwritten.

    Returns `(created, removed)`.
    """
    created = []
    removed = []

    for example_name, target_name in (
        (".env.example", ".env"),
        (".env.staging.example", ".env.staging"),
        (".env.prod.example", ".env.prod"),
    ):
        example = ROOT / example_name
        target = ROOT / target_name

        if not example.exists():
            if not target.exists():
                print(f"  warning: {example_name} is missing, skipping")
            continue

        if target.exists():
            print(f"  {target_name} already exists, leaving it alone")
        else:
            text = example.read_text(encoding="utf-8")
            text = text.replace("SECRET_KEY=", f"SECRET_KEY={secrets.token_urlsafe(50)}", 1)
            target.write_text(text, encoding="utf-8")
            created.append(target_name)

        example.unlink()
        removed.append(example_name)

    return created, removed


def ignore_boilerplate_files():
    """
    Keep the boilerplate's own documentation out of your repository.

    `docs/` stays on disk -- you and your AI tools still read it -- it simply never
    enters your history.

    Delete the line from .gitignore if you would rather your team had it too.
    """
    gitignore = ROOT / ".gitignore"

    if not gitignore.exists():
        print("  warning: no .gitignore, skipping")
        return []

    text = gitignore.read_text(encoding="utf-8")
    present = {line.strip() for line in text.splitlines()}

    if "docs/" in present:
        return []

    gitignore.write_text(
        f"{text.rstrip()}\n\n# Boilerplate's own docs: yours to read, not to ship\ndocs/\n",
        encoding="utf-8",
    )
    return ["docs/"]


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


def clean_up_self():
    """
    Remove this script and its marker, now that both have done their one job.

    Runs before the folder rename, while these paths still resolve. Deleting a running
    script is safe -- Python has already read it -- and it is the last thing left that
    belongs to the boilerplate rather than to you.
    """
    removed = []
    for path in (MARKER, Path(__file__).resolve()):
        try:
            path.unlink()
            removed.append(path.name)
        except OSError as exc:
            print(f"  warning: could not delete {path.name} ({exc.strerror}) -- delete it yourself")
    return removed


def rename_root(name):
    """
    Rename the project directory itself, and return its new path.

    Runs last, because every step before it writes through the old path. Your shell
    is still sitting in the directory under its old name afterwards, which no longer
    exists -- `cd` to the printed path before running anything else.

    Returns None when the folder is already named that, when something else there
    already has the name, or when the rename is refused.
    """
    if ROOT.name == name:
        return None

    target = ROOT.parent / name

    if target.exists():
        print(f"  warning: {target.name}/ already exists next door, leaving the folder name alone")
        return None

    try:
        ROOT.rename(target)
    except OSError as exc:
        print(f"  warning: could not rename the folder ({exc.strerror}) -- rename it yourself")
        return None

    return target


def main():
    parser = argparse.ArgumentParser(description="Turn this boilerplate into your project.")
    parser.add_argument("name", help="your project name, e.g. my_project")
    args = parser.parse_args()

    if MARKER.exists():
        fail(
            "an earlier run stopped partway -- .bootstrapped is still here.\n"
            "  Check what it left behind, then delete .bootstrapped and run this again."
        )

    print(f"\n  Setting up '{args.name}'\n")

    MARKER.write_text(f"{args.name}\n", encoding="utf-8")

    created, removed = write_env_files()
    if created:
        print(f"  wrote {', '.join(created)}, each with its own fresh SECRET_KEY")
    if removed:
        print(f"  removed {len(removed)} .example template(s) -- the real files replace them")

    cleared = clear_migrations()
    print(f"  cleared {cleared} boilerplate migration file(s)")

    ignored = ignore_boilerplate_files()
    if ignored:
        print(f"  added {', '.join(ignored)} to .gitignore -- still on disk, just not committed")

    rewrite_titles(args.name)
    print(f"  set the API documentation title to '{title_from(args.name)} API'")

    if reset_git():
        print("  replaced the boilerplate's git history with a fresh repository")

    if clean_up_self():
        print("  deleted bootstrap.py and its marker -- there is nothing left to run twice")

    # Last: everything above writes through the old path.
    renamed = rename_root(args.name)
    if renamed:
        print(f"  renamed the folder to {renamed.name}/")

    if renamed:
        intro = "Done. Your shell is still in the old folder name, so start with the cd:"
        first_step = f"cd ../{renamed.name}\n    "
    else:
        intro = "Done. Next:"
        first_step = ""

    print(
        f"""
  {intro}

    {first_step}python -m venv .venv && source .venv/bin/activate
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
"""
    )


if __name__ == "__main__":
    main()
