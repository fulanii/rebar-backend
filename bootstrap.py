#!/usr/bin/env python3
"""
Turn this boilerplate into your project.

    python rebar-backend/bootstrap.py my_saas

Run it from the folder above, not from inside: the last thing it does is rename the
folder, and a shell standing in a renamed folder is left pointing at nothing.

Creates .env, .env.staging and .env.prod with fresh secret keys and removes the
.example templates they replace, clears the boilerplate's migrations, sets the API
documentation title, gitignores the boilerplate's docs, deletes the boilerplate's git
history, renames the project folder to your project name, and deletes itself.

It does not run `git init`, that first commit is yours to make.

Run it once, immediately after cloning.

Standard library only, so it runs before you have installed anything.
"""

import argparse
import secrets
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER = ROOT / ".bootstrapped"
STARTED_IN = Path.cwd().resolve()


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
        text = text.replace('"TITLE": "Rebar API"', f'"TITLE": "{title} API"')
        settings_base.write_text(text, encoding="utf-8")

    readme = ROOT / "readme.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        text = text.replace("# Rebar Backend", f"# {title} Backend", 1)
        readme.write_text(text, encoding="utf-8")


def write_env_files():
    """
    Create .env, .env.staging and .env.prod from their .example templates.

    Each gets its own generated SECRET_KEY, so a leaked development key cannot forge
    production sessions. Only .env is ever loaded; the other two are yours to fill in
    and copy from.

    Each template is deleted once its real file exists, the real file carries the
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

    `docs/` stays on disk, where you and your AI tools still read it. It simply never
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


def remove_git():
    """
    Delete the boilerplate's history, leaving the folder with no repository at all.

    Your project is not a fork of mine and its history should not start as one. Run
    `git init` yourself when you are ready, the first commit is then genuinely yours,
    made when you choose and with the name and email you meant to use.
    """
    git_dir = ROOT / ".git"
    if not git_dir.exists():
        return False

    shutil.rmtree(git_dir)
    return True


def clean_up_self():
    """
    Remove this script and its marker, now that both have done their one job.

    Runs before the folder rename, while these paths still resolve. Deleting a running
    script is safe, because Python has already read it, and it is the last thing left
    that belongs to the boilerplate rather than to you.
    """
    removed = []
    for path in (MARKER, Path(__file__).resolve()):
        try:
            path.unlink()
            removed.append(path.name)
        except OSError as exc:
            print(f"  warning: could not delete {path.name} ({exc.strerror}). Delete it yourself")
    return removed


def rename_root(name):
    """
    Rename the project directory itself, and return its new path.

    Runs last, because every step before it writes through the old path.

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
        print(f"  warning: could not rename the folder ({exc.strerror}), rename it yourself")
        return None

    return target


def cd_into(project):
    """
    The `cd` that lands the shell in the finished project, or "" if it is already there.

    A shell that was sitting inside the folder when it was renamed is now pointing at a
    path that no longer exists, so it has to climb out and back in. A shell that ran the
    script from outside (`python rebar-backend/bootstrap.py my_saas`) just
    walks in.
    """
    if project == STARTED_IN:
        return ""
    if STARTED_IN == ROOT:
        return f"cd ../{project.name}"
    try:
        return f"cd {project.relative_to(STARTED_IN)}"
    except ValueError:
        return f"cd {project}"


def main():
    parser = argparse.ArgumentParser(description="Turn this boilerplate into your project.")
    parser.add_argument("name", help="your project name, e.g. my_project")
    args = parser.parse_args()

    if MARKER.exists():
        fail(
            "an earlier run stopped partway, .bootstrapped is still here.\n"
            "  Check what it left behind, then delete .bootstrapped and run this again."
        )

    print(f"\n  Setting up '{args.name}'\n")

    MARKER.write_text(f"{args.name}\n", encoding="utf-8")

    created, removed = write_env_files()
    if created:
        print(f"  wrote {', '.join(created)}, each with its own fresh SECRET_KEY")
    if removed:
        print(f"  removed {len(removed)} .example template(s), the real files replace them")

    cleared = clear_migrations()
    print(f"  cleared {cleared} boilerplate migration file(s)")

    ignored = ignore_boilerplate_files()
    if ignored:
        print(f"  added {', '.join(ignored)} to .gitignore, still on disk, just not committed")

    rewrite_titles(args.name)
    print(f"  set the API documentation title to '{title_from(args.name)} API'")

    if remove_git():
        print("  deleted the boilerplate's git history. Run `git init` when you are ready")

    if clean_up_self():
        print("  deleted bootstrap.py and its marker. Nothing is left to run twice")

    # Last: everything above writes through the old path.
    renamed = rename_root(args.name)
    if renamed:
        print(f"  renamed the folder to {renamed.name}/")

    step = cd_into(renamed or ROOT)
    first_step = f"{step}\n    " if step else ""

    print(f"""
  Done. Next:

    {first_step}python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt
    python manage.py makemigrations
    python manage.py migrate
    python manage.py runserver

  Then open http://localhost:8000/docs/

  .env is the only file the app loads. .env.staging and .env.prod are yours to
  fill in and copy from, switch environment by changing DJANGO_SETTINGS_MODULE
  inside .env, or set the values in your host's dashboard.

  This folder is no longer a git repository. Once the tests are green, `git init`
  and make the first commit your own, docs/getting-started.md walks through it.

  Configuration:  docs/configuration.md
  Deployment:     docs/deployment.md
  Before your first change: docs/ai/guardrails.md
""")


if __name__ == "__main__":
    main()
