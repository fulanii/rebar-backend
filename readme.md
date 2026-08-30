# SaaS Boilerplate — Backend

A production-ready Django REST Framework backend for the part of every SaaS that is
identical every time: Clone it, rename it, and start building your actual
product on top.

Built to be worked on **through AI tools**. The structure is regular, the rules are
written down in [`docs/ai/`](docs/ai/), and [`CLAUDE.md`](CLAUDE.md) /
[`AGENTS.md`](AGENTS.md) point your assistant at them automatically.

---

## What's in it

**Authentication is complete** — 260 tests, all green, covering the failure paths as
well as the happy ones.

| | |
|---|---|
| **Accounts** | Register with name, email, US phone and password. Read your own profile. |
| **Email verification** | 6-digit code, hashed at rest, single-use, 15-minute expiry. Resending invalidates the previous code. |
| **Passwords** | Reset by emailed code; change while signed in, current password required. |
| **Google sign-in** | Server-side redirect flow. Works on mobile, where the popup button does not. |
| **Sessions** | Access token in the body, refresh token in an httpOnly cookie, rotation with blacklisting, real logout. |
| **Suspension** | Enforced on every request, not just at login. |
| **Rate limits** | Per endpoint, on everything unauthenticated. |
| **Email delivery** | Brevo or Resend, chosen by one env var. Templates live in their dashboard. |
| **API reference** | Swagger at `/docs/`, generated from the code, development only. |
| **Project setup** | Four settings modules, `bootstrap.py`, CI, pre-commit, and the `docs/ai/` rule set. |

Billing, background jobs, an admin back-office and more are the layers most projects
add next — see the [roadmap](docs/roadmap.md) for what is planned and what is left out
on purpose.

---

## Quickstart

```bash
git clone <this repo> && cd backend-saas-boilerplate
python bootstrap.py my_project
cd ../my_project          # bootstrap renames the folder

python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python manage.py makemigrations && python manage.py migrate
python manage.py runserver
```

Open **http://localhost:8000/docs/**. Runs on SQLite with no setup at all, and
`pytest` should be green before you go further.

**[docs/getting-started.md](docs/getting-started.md)** takes it from here: filling in
`.env`, wiring up email and Google sign-in, setting up your branches, and pointing
your AI tool at the rules.

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
| POST | `/token/` | Standard SimpleJWT token pair; prefer `/auth/login/` |
| POST | `/token/refresh/` | New access token from the cookie |
| POST | `/token/blacklist/` | Sign out |

Full request and response documentation for each is on the Swagger page, generated
from the docstrings in the code.

---

## Documentation

| Guide | Covers |
|---|---|
| [getting-started.md](docs/getting-started.md) | Clone to first deploy, step by step |
| [configuration.md](docs/configuration.md) | Every environment variable — what it does, what breaks without it |
| [email-templates.md](docs/email-templates.md) | Building the two email templates (Brevo or Resend) |
| [git-workflow.md](docs/git-workflow.md) | Branching, pull requests, and why you never push to `main` |
| [deployment.md](docs/deployment.md) | Shipping to Railway and similar platforms |
| [roadmap.md](docs/roadmap.md) | What is built, planned, and deliberately absent |

And in [`docs/ai/`](docs/ai/), the house rules — written for an assistant, useful to
anyone:

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

I'm **Yassine**, a backend engineer, and I'm **open to backend work** — Django/DRF/FastAPI
APIs, Stripe and payments, third-party integrations, and taking a prototype the rest
of the way to production.

- Portfolio: **[yassinecodes.dev](https://yassinecodes.dev)**
- Email: **[yassine@yassinecodes.dev](mailto:yassine@yassinecodes.dev)**

Happy to hear about contract work, a full-time role, or just what you ended up
building with this.
