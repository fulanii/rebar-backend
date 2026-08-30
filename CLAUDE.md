# Working in this codebase

Django REST Framework backend. Email-first JWT authentication with Google OAuth.
Python 3.13, Django 5.2, DRF 3.16, PostgreSQL, Celery.

Read `docs/ai/guardrails.md` before your first change. It is short and it is the
difference between a change that ships and one that quietly breaks logins.

## Layout

```
config/          settings (base/dev/staging/prod), root urls, middleware, schema tests
authentication/  the only app: users, JWT, verification, password reset, Google OAuth
docs/            configuration and deployment guides
docs/ai/         how to work here -- architecture, conventions, guardrails, recipes
```

Inside an app, every layer is a package of small modules, one concern per file:

```
authentication/
├── models/       one file per model, re-exported from models/__init__.py
├── serializers/  request and response shapes + shared field validators
├── views/        one file per endpoint; a subpackage when a flow has several
├── utils/        cookies, code generation, email, Google helpers
├── tests/        mirrors the structure above: tests/models, tests/views, ...
├── auth.py       the project-wide authentication class
├── throttles.py  one throttle class per named rate scope
└── urls.py       routes, mounted in config/urls.py
```

## Commands

```bash
pytest                      # run every test
pytest authentication -q    # one app
black . && isort . && flake8 .   # formatting and lint, exactly what CI runs
python manage.py runserver  # then open http://localhost:8000/docs/
python manage.py makemigrations && python manage.py migrate
```

CI fails on any formatting difference, any lint error, a missing migration, or a
failing test. Run the three commands above before you say you are done.

## Hard rules

1. **Never put the refresh token in a response body.** It goes in the httpOnly
   cookie via `authentication/utils/cookies.py`. Only the access token is returned.
2. **Never weaken or remove a throttle to make something pass.** The rate limits are
   what make a 6-digit code safe to email. Fix the test instead.
3. **Text fields are `blank=True`, never `null=True`.** Absent means `""`.
4. **Every HTTP method on a view needs a docstring** in the house format -- it *is*
   the API documentation and a test enforces it. See `docs/ai/conventions.md`.
5. **Never edit a migration that has already been applied.** Make a new one.
6. **No secrets in code**, including in docstring examples. They go in the
   gitignored `.env`.
7. **Authentication endpoints must not reveal whether an email is registered.**
   Wrong password, unknown address and expired code all return the same message.
8. **Add tests with every endpoint.** Cover the failure paths, not just the success.
9. **Never adopt an unverified account without discarding its password** — see
   guardrail 11. A social login proves the address, not the password on the row.
10. **Never commit or push to `main` or `staging`.** Branch, push the branch, open a
    pull request. Those two branches deploy, and CI only runs on pull requests. See
    `docs/git-workflow.md`.
11. **Do not add explanatory comments.** This codebase is almost comment-free by
   design — reasoning lives in `docs/`, not above the line. One-line module
   docstrings, tool directives and view API docstrings only. See
   `docs/ai/conventions.md`.

## Where things go

Adding an endpoint touches four files, in this order:
serializer → view → `urls.py` → tests. Plus a throttle class and its rate in
`settings/base.py` if the endpoint needs a new limit.

Step-by-step: `docs/ai/recipes/add-an-endpoint.md`.

## Before you finish

- `pytest` green, `black --check . && isort --check-only . && flake8 .` clean.
- New endpoint documented in its docstring and reachable at `/docs/`.
- No new dependency without adding it, pinned, to `requirements.txt`.
