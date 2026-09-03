# Working in this codebase

Django REST Framework backend. Email-first JWT authentication with Google OAuth.
Python 3.13, Django 6.1, DRF 3.18, SimpleJWT, PostgreSQL, Celery.

Read `docs/ai/guardrails.md` before your first change. It is short and it is the
difference between a change that ships and one that quietly breaks logins.

## Layout

```
config/          settings (base/dev/staging/prod), root urls, middleware,
                 and the tests that guard the conventions
authentication/  accounts, JWT, verification, passwords, email change,
                 account deletion, Google OAuth
docs/            endpoints, configuration, email templates, background jobs,
                 deployment, git
docs/ai/         how to work here, architecture, conventions, guardrails, recipes
```

One app per domain. A new one sits beside `authentication/` and copies its shape,
`docs/ai/recipes/add-an-app.md` has the steps. Inside an app, every layer is a package
of small modules, one concern per file:

```
authentication/
├── models/       one file per model, re-exported from models/__init__.py
├── serializers/  request and response shapes + shared field validators
├── views/        one file per endpoint; a subpackage when a flow has several
├── utils/        cookies, code generation, email, Google helpers
├── tests/        mirrors the structure above: tests/models, tests/views, ...
├── auth.py       the project-wide authentication class
├── tasks/        background jobs, one per file; email is queued, never sent
│                 in the request
├── throttles.py  one throttle class per named rate scope
└── urls.py       routes, mounted in config/urls.py
```

## Commands

```bash
pytest                      # run every test
pytest authentication -q    # one app
black . && isort . && flake8 .   # formatting and lint, exactly what CI runs
python manage.py runserver  # then open http://localhost:8000/docs/
celery -A config worker     # only when CELERY_BROKER_URL is set; else jobs run inline
python manage.py makemigrations && python manage.py migrate
```

CI fails on any formatting difference, any lint error, a missing migration, or a
failing test. Run the three commands above before you say you are done.

With `pre-commit install`, the formatters and linters run on every commit and the full
suite runs on every push, so the same checks happen whether or not you remember.

## Hard rules

They are not listed here. Kept in two places they drift, and the copy an assistant
reads is the one that goes stale. Each lives in exactly one file:

| | |
|---|---|
| [`docs/ai/guardrails.md`](docs/ai/guardrails.md) | **Read before your first change.** The mistakes that leave the tests green and the app apparently working: the refresh token, the throttles, session revocation, what an auth endpoint may reveal, account takeover, migrations, secrets. |
| [`docs/ai/conventions.md`](docs/ai/conventions.md) | The house style, and it is enforced: file layout, imports, size limits, the API docstring on every method, and why there are no explanatory comments. |
| [`docs/git-workflow.md`](docs/git-workflow.md) | Never commit or push to `main` or `staging`. Branch, push the branch, open a pull request. Those two branches deploy, and CI only runs on pull requests. |

Read the first two before touching anything. Most of what they say is enforced by
`config/tests/`, so a shortcut fails the build rather than reaching production, but the
build only catches what somebody thought to write a test for. The reasoning is in the
docs, and the reasoning is the part that stops you making a new mistake.

## Where things go

Adding an endpoint touches four files, in this order:
serializer → view → `urls.py` → tests. Plus a throttle class and its rate in
`settings/base.py` if the endpoint needs a new limit.

Step-by-step: `docs/ai/recipes/add-an-endpoint.md`.

## Before you finish

- `pytest` green, `black --check . && isort --check-only . && flake8 .` clean.
- New endpoint documented in its docstring and reachable at `/docs/`.
- No new dependency without adding it, pinned, to `requirements.txt`.
