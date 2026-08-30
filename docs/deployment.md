# Deployment

Written for platforms that build straight from a Git repository — Railway, Render,
Fly, Heroku. You connect the repo, set environment variables in a dashboard, and each
merge deploys.

There is no Dockerfile and no Procfile. These platforms detect a Python project and
install `requirements.txt` on their own; you tell them how to run it in the dashboard,
which is less to maintain than an image you have to keep patched.

## Start and release commands

Set these in your platform's settings.

**Start command:**

```
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 60 --access-logfile - --error-logfile -
```

`$PORT` is injected by the platform. Do not hardcode 8000. `--workers 3` is a starting
point — more workers need more memory, so tune it against real traffic. Logging to `-`
sends the logs to stdout, where the platform collects them.

**Pre-deploy / release command:**

```
python manage.py migrate --noinput
```

Railway calls this a pre-deploy command, Render a pre-deploy command, Heroku a release
phase. Whatever it is called, it runs **before** the new version takes traffic — so
migrations are applied while the *old* code is still serving requests.

That ordering is why a migration must be backwards-compatible with the version it is
replacing: adding a column is safe; dropping one the running code still selects is
not. Split a rename into two deploys — add the new column, ship code that uses it,
then remove the old one.

If your platform has no release hook, run `migrate` yourself from its shell before
promoting the new version. Do not put `migrate` in the start command: with several
workers booting at once you get several concurrent migrations.

## The two-environment setup

| Branch | Service | Settings module |
|---|---|---|
| `staging` | staging | `config.settings.staging` |
| `main` | production | `config.settings.prod` |

Create two services from the same repository, each watching its own branch, each with
its own database, its own Redis, and its own environment variables. Merging to
`staging` deploys staging; merging to `main` deploys production.

Point CI at both branches — it already runs on pull requests into either.

## Environment variables

Set them in the platform's dashboard rather than committing an env file. A real
environment variable beats the file, so no `.env` needs to exist at all.

Every variable is documented in [configuration.md](configuration.md). The ones a
deployment cannot start without:

```
DJANGO_SETTINGS_MODULE   config.settings.prod   (or .staging)
SECRET_KEY               unique per environment
ALLOWED_HOSTS            your API's hostname
CORS_ALLOWED_ORIGINS     your frontend's origin
FRONTEND_URL             your frontend's base URL
DOMAIN                   bare domain, for the refresh cookie
DB_NAME DB_USER DB_PASSWORD DB_HOST
REDIS_URL                required — see below
BREVO_API_KEY            or nobody can verify an email (or RESEND_API_KEY)
VERIFICATION_TEMPLATE_ID and PASSWORD_RESET_TEMPLATE_ID
```

Production deliberately fails at boot when one of these is missing, rather than
starting in a state that half works.

### Redis is not optional

You will be running more than one worker, and the Google sign-in flow needs all of
them to share one cache. Without it, logins fail intermittently in a way that is
genuinely hard to diagnose. Add the platform's Redis add-on and set `REDIS_URL`.

## Add-ons to provision

- **Postgres** — one per environment. Never let staging point at the production
  database; a staging test that deletes rows would delete real ones.
- **Redis** — one per environment.

## After the first deploy

1. Add the deployed callback URL to your Google OAuth client's authorized redirect
   URIs: `https://api.example.com/auth/google/callback/`. Exactly, trailing slash
   included.
   on it.
2. Create an admin account: `python manage.py createsuperuser` through the
   platform's shell. Note that the Django admin is not mounted outside development —
   the superuser flags exist for your own tooling.
3. Check `/docs/` returns 404 in production. If it does not, `DJANGO_SETTINGS_MODULE`
   is wrong.

## Static files

Nothing is served from disk. The API returns JSON only; the browsable API, Swagger
and the Django admin — the three things that need static files — are all confined to
development. If you later mount any of them in a deployed environment, add
`whitenoise` and run `collectstatic`.

## Health checks

Point the platform's health check at any cheap endpoint. `GET /auth/me/` without a
token returns a fast 401, which proves the app and its settings loaded. If you want a
real check that touches the database, add a health endpoint — see
`docs/ai/recipes/add-an-endpoint.md`.

## Rolling back

Redeploy the previous commit from the platform's dashboard. **Migrations do not roll
back with it.** That is the reason for the backwards-compatibility rule above: the
previous version has to be able to run against the newer database.
