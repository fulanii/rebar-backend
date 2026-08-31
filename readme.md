# SaaS Boilerplate — Backend

A real production-ready Django REST Framework backend for the part of every SaaS that is
identical every time: Clone it, rename it, and start building your actual
product on top.

Built to be worked on **through AI tools**. The structure is regular, the rules are
written down in [`docs/ai/`](docs/ai/), and [`CLAUDE.md`](CLAUDE.md) /
[`AGENTS.md`](AGENTS.md) point your assistant at them.

---

## What's in it

**Authentication is complete** — 407 tests, all green, covering the failure paths as
well as the happy ones.

| | |
|---|---|
| **Accounts** | Register with name, email, US phone and password. Change your email address, delete your account. Unverified addresses cannot be squatted. |
| **Email verification** | 6-digit code, hashed at rest, single-use, 15-minute expiry, dead after 5 wrong guesses. Resending invalidates the previous code. |
| **Passwords** | Reset by emailed code, which signs out every device — access tokens included; change while signed in, current password required. Both email a notification. |
| **Google sign-in** | Server-side redirect flow. Works on mobile, where the popup button does not. |
| **Sessions** | Access token in the body, refresh token in an httpOnly cookie, rotation with blacklisting, real logout. |
| **Suspension** | Enforced on every request, not just at login. |
| **Rate limits** | Every route, with its own scope. A test fails if a view forgets one. |
| **Email delivery** | Brevo or Resend, chosen by one env var. Templates live in their dashboard. |
| **Background jobs** | Celery. Email is queued, retried with backoff, and never blocks a request. Runs inline until you set a broker. |
| **API reference** | Swagger at `/docs/`, generated from the code, development only. |
| **Project setup** | Four settings modules, `bootstrap.py`, CI, pre-commit, and the `docs/ai/` rule set. |

Billing, background jobs, an admin back-office and more are the layers most projects
add next — see the [roadmap](docs/roadmap.md) for what is planned and what is left out
on purpose.

---

## Quickstart

```bash
git clone <this repo>
python backend-saas-boilerplate/bootstrap.py my_saas
cd my_saas

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

Seventeen routes: accounts, email verification, passwords, Google sign-in and
sessions. **[docs/endpoints.md](docs/endpoints.md)** lists them all; the Swagger page
at `/docs/` has the full request and response shape for each, generated from the code.

---

## Documentation

| Guide | Covers |
|---|---|
| [getting-started.md](docs/getting-started.md) | Clone to first deploy, step by step |
| [endpoints.md](docs/endpoints.md) | Every route, grouped, with what each one is for |
| [configuration.md](docs/configuration.md) | Every environment variable — what it does, what breaks without it |
| [email-templates.md](docs/email-templates.md) | Building the four email templates (Brevo or Resend) |
| [background-jobs.md](docs/background-jobs.md) | Celery: what is queued, running a worker, and deploying one |
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
| [`recipes/`](docs/ai/recipes/) | Step-by-step: adding an endpoint, a model, an app, an email, an account-keyed throttle |
| [`glossary.md`](docs/ai/glossary.md) | Every term in plain English, no experience assumed |

---

## License

[MIT](LICENSE) — use it commercially, modify it, ship it closed-source, no attribution
in your product required. It is provided as is, with no warranty and no liability:
what you deploy and how you secure it is yours.

Keep the `LICENSE` file if you redistribute the boilerplate itself. If you are building
your own product on it, replace it with whatever licence your product needs.

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
