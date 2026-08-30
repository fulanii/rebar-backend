# SaaS Boilerplate — Backend

A production-ready Django REST Framework backend for the part of every SaaS that is
identical every time: accounts. Clone it, rename it, and start building your actual
product on top.

Built to be worked on **through AI tools**. The structure is regular, the rules are
written down in [`docs/ai/`](docs/ai/), and [`CLAUDE.md`](CLAUDE.md) /
[`AGENTS.md`](AGENTS.md) point your assistant at them automatically.

## What you get

- **Email + password accounts** — registration collecting name, email and US phone.
- **6-digit email verification**, hashed at rest, single-use, 15-minute expiry, with
  a resend endpoint that invalidates the previous code.
- **Password reset** by emailed code, and password change while signed in.
- **Brevo or Resend** for email — one env var picks the provider, templates live in
  their dashboard so copy changes need no deploy.
- **Sign in with Google** — the server-side redirect flow, which works on mobile
  where Google's popup button does not.
- **JWT sessions done properly** — short-lived access token in the body, refresh
  token in an httpOnly cookie, rotation with blacklisting, real logout.
- **Account suspension** that takes effect on the very next request.
- **Per-endpoint rate limits** on everything unauthenticated.
- **Interactive API docs** at `/docs/`, generated from the code.
- **A test suite** covering the failure paths, not just the happy ones.

Deliberately **not** included: billing, background jobs, an admin panel, file
uploads, SMS. They are the next layers, and every project wants them differently.

---

## Getting started

### 1. Clone it and make it yours

```bash
git clone <this repo> my-project && cd my-project
python bootstrap.py my_project
```

`bootstrap.py` writes `.env`, `.env.staging` and `.env.prod` — each with its own
generated `SECRET_KEY` — clears the boilerplate's migrations, titles the API docs
after your project, and replaces this repo's git history with a fresh one, so your
first commit is genuinely your first commit.

Run it once, before anything else. It refuses to run twice.

### 2. Install and run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

Open **http://localhost:8000/docs/** — every endpoint, with its request and response
shapes, generated from the code.

Runs on SQLite with no setup at all.

### 3. Check it works

```bash
pytest
```

Green means the whole auth flow works on your machine. If it isn't, stop here — every
step below assumes it is.

### 4. Fill in `.env`

The app runs without any of these; each one switches on a feature.

| To get | Set |
|---|---|
| Verification and password-reset emails | `EMAIL_PROVIDER` (`brevo` or `resend`), that provider's API key, and the two template ids — see [docs/email-templates.md](docs/email-templates.md) |
| Sign in with Google | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — see [docs/configuration.md](docs/configuration.md) |

**Nobody can finish registering until the email templates exist**, since verification
is part of signing up. Do that before your first real user.

### 5. Set up your branches

```bash
git add -A && git commit -m "Initial commit"
git branch -M main
git checkout -b staging

# create an empty repo on GitHub, then:
git remote add origin git@github.com:you/my-project.git
git push -u origin main staging
```

Two long-lived branches: `staging` deploys to your staging service, `main` to
production.

**Never commit to either of them directly.** The loop is:

```
branch off staging  →  push the branch  →  pull request  →  merge
                                                              ↓
                    git checkout staging && git pull  ←───────┘
```

CI runs on pull requests **only**, so a direct push to `main` runs no formatter, no
linter, no migration check and no tests — and deploys anyway. Turn on branch
protection for both branches so the rule holds even at 2am.

[docs/git-workflow.md](docs/git-workflow.md) has the commands, the protection
settings, and how to recover if you commit to `main` by accident.
[docs/deployment.md](docs/deployment.md) covers shipping.

### 6. Point your AI tool at the docs

Most tools read [`CLAUDE.md`](CLAUDE.md) or [`AGENTS.md`](AGENTS.md) automatically, so
usually there is nothing to do. If yours does not, start a session with:

> Read `CLAUDE.md`, `docs/ai/guardrails.md`, `docs/ai/architecture.md` and
> `docs/ai/conventions.md` before making any changes. Follow the recipes in
> `docs/ai/recipes/` when adding an endpoint, a model or an app.

Read [`docs/ai/guardrails.md`](docs/ai/guardrails.md) yourself too, even if you never
open the code. It is short, and it is the list of things that quietly break this
project — the kind of change an assistant will happily make if you ask it to "just get
the tests passing".

### 7. Start building

Add your own app beside `authentication/`:
[docs/ai/recipes/add-an-app.md](docs/ai/recipes/add-an-app.md).

---

## The endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register/` | Create an account; emails a 6-digit code |
| POST | `/auth/verify-email/` | Submit the code; activates the account |
| POST | `/auth/resend-verification/` | New code; invalidates the previous one |
| POST | `/auth/login/` | Access token + profile, refresh cookie set |
| GET | `/auth/me/` | The signed-in user's profile |
| POST | `/auth/password-reset/` | Email a reset code |
| POST | `/auth/password-reset/confirm/` | Code + new password |
| POST | `/auth/change-password/` | Change password while signed in |
| GET | `/auth/google/login/` | Start Google sign-in (navigate, don't fetch) |
| GET | `/auth/google/callback/` | Google returns here |
| POST | `/auth/google/exchange/` | Handoff code → tokens |
| POST | `/token/refresh/` | New access token from the cookie |
| POST | `/token/blacklist/` | Sign out |

Full request and response documentation for each is in the Swagger page, generated
from the docstrings in the code.

---

## Configuration

Everything comes from environment variables. **The app loads exactly one file:
`.env`.** Which settings module runs is a line inside it:

```
DJANGO_SETTINGS_MODULE=config.settings.dev      # or .staging, or .prod
```

`bootstrap.py` also writes `.env.staging` and `.env.prod`, each with its own generated
`SECRET_KEY`. **Those two are never loaded** — they are where you keep each
environment's values, so you can see at a glance what is in use where, and copy from
them into `.env` or into your host's dashboard.

A real environment variable always beats the file, so on a host where you set values
in a dashboard, no `.env` needs to exist at all.

**[docs/configuration.md](docs/configuration.md) documents every variable** — what it
does, when it is required, and what breaks without it. Three worth knowing up front:

- `SECRET_KEY` — different in every environment. A leaked dev key must not be able to
  forge production sessions.
- `REDIS_URL` — required as soon as you run more than one worker, or Google sign-in
  fails intermittently.
- `GOOGLE_CLIENT_ID` / `_SECRET` — the callback URL must match what you registered
  with Google exactly, trailing slash included. This is the usual reason it fails.

---

## Development

```bash
pytest                            # the whole suite
pytest authentication -q          # one app
black . && isort . && flake8 .    # exactly what CI runs
pre-commit install                # run the above automatically before each commit
```

CI fails on any formatting difference, lint error, missing migration, or failing test.

### Reading a verification code locally

Without a Resend key, no email is sent. The code is hashed in the database and cannot
be read back — for local testing either set a real key, or temporarily log the raw
code in `authentication/views/user_registration.py` and remove that line before
committing.

---

## Deploying

Built for platforms that deploy from a Git repository — Railway, Render, Fly, Heroku.
Connect the repo, set environment variables in the dashboard, and each merge ships.

The usual setup is two services from one repository: `staging` branch →
`config.settings.staging`, `main` branch → `config.settings.prod`, each with its own
database and Redis.

There is no Dockerfile and no Procfile — these platforms install `requirements.txt`
themselves, and you give them the start and release commands in the dashboard.

**[docs/deployment.md](docs/deployment.md)** has those commands, plus the
branch/service setup, the add-ons to provision, the migration-ordering rule that makes
rollbacks survivable, and what to do after the first deploy.

Production enforces HTTPS, sets HSTS, and does **not** mount the API docs or the
Django admin. Publishing your full API surface, and adding a login form to attack, are
both avoidable.

---

## Documentation

| Guide | Covers |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) | The rules an AI assistant must follow. Read automatically by most tools |
| [docs/configuration.md](docs/configuration.md) | Every environment variable — what it does, what breaks without it |
| [docs/email-templates.md](docs/email-templates.md) | Building the two email templates (Brevo or Resend) |
| [docs/git-workflow.md](docs/git-workflow.md) | Branching, pull requests, and why you never push to `main` |
| [docs/deployment.md](docs/deployment.md) | Shipping to Railway and similar platforms |
| `/docs/` when running | The interactive API reference, generated from the code |

And in [`docs/ai/`](docs/ai/), the house rules:

| Guide | Covers |
|---|---|
| [`guardrails.md`](docs/ai/guardrails.md) | The mistakes that are easy to make here, and what each one breaks. **Read this one yourself** |
| [`architecture.md`](docs/ai/architecture.md) | How a request flows through the app, and where each kind of file goes |
| [`conventions.md`](docs/ai/conventions.md) | The house style |
| [`recipes/`](docs/ai/recipes/) | Step-by-step: adding an endpoint, a model, an app, an email |
| [`glossary.md`](docs/ai/glossary.md) | Every term in plain English, no experience assumed |

---

## Found this useful?

**Give it a star** — it costs you a click and it genuinely helps other people find it.

I'm **Yassine**, a backend engineer, and I'm **open to backend work** — Django/DRF
APIs, Stripe and payments, third-party integrations, and taking a prototype the rest
of the way to production.

- Portfolio: **[yassinecodes.dev](https://yassinecodes.dev)**
- Email: **[yassine@yassinecodes.dev](mailto:yassine@yassinecodes.dev)**

Happy to hear about contract work, a full-time role, or just what you ended up
building with this.
