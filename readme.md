# SaaS Boilerplate Backend

**The backend every SaaS rebuilds from scratch: accounts, billing, admin and waitlist,
built once, properly, and tested.** Clone it, rename it, start building the product you
actually wanted to build.

Django REST Framework, Python 3.13, PostgreSQL, Redis, Celery.

**Authentication ships today**, complete and covered by **407 tests**: register →
verify → sign in → reset → Google → sign out, with the security decisions already made
and written down. Billing on Stripe, an admin back-office and a waitlist are the layers
landing next, built to the same standard.

It is also built to be worked on **through AI tools**, which is a different problem
from being readable. Every rule an assistant could get wrong is written down in
[`docs/ai/guardrails.md`](docs/ai/guardrails.md), 16 of them, each with the failure it
causes, and [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) point your assistant at
them the moment it opens the repo. The structure is regular enough that it cannot
invent a second way to do anything, and the build fails if it tries.

---

## Running in about a minute

```bash
git clone <this repo>
python backend-saas-boilerplate/bootstrap.py my_saas
cd my_saas

python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python manage.py makemigrations && python manage.py migrate
python manage.py runserver
```

Open **http://localhost:8000/docs/** for the API reference, generated from the code.
SQLite, no database to install, no services to run, and `pytest` should be green
before you go any further.

**📖 [Documentation](docs/)**, setup, configuration, deployment, and the house rules.

---

## Shipped

**Authentication and accounts**, eighteen endpoints, [the full list](docs/endpoints.md).

| | |
|---|---|
| **Accounts** | Register with name, email, US phone and password. Update your profile, change your email address, delete your account. Unverified addresses cannot be squatted. |
| **Email verification** | 6-digit code, hashed at rest, single-use, 15-minute expiry, dead after 5 wrong guesses. Resending invalidates the previous code. |
| **Passwords** | Reset by emailed code, which signs out every device, access tokens included; change while signed in, current password required. Both email a notification. |
| **Google sign-in** | Server-side redirect flow. Works on mobile, where the popup button does not. |
| **Sessions** | Access token in the body, refresh token in an httpOnly cookie, rotation with blacklisting, real logout. |
| **Suspension** | Enforced on every request, not just at login. |
| **Rate limits** | Every route, with its own scope. A test fails if a view forgets one. |
| **Email delivery** | Brevo or Resend, chosen by one env var. Templates live in their dashboard. |
| **Background jobs** | Celery. Email is queued, retried with backoff, and never blocks a request. Runs inline until you set a broker. |
| **API reference** | Swagger at `/docs/`, generated from the code, development only. |
| **Project setup** | Four settings modules, `bootstrap.py`, CI, pre-commit, and the `docs/ai/` rule set. |

---

## Landing next

Not started yet, and listed here so you know where this is going rather than as a
promise of dates. The [roadmap](docs/roadmap.md) has the detail.

| | |
|---|---|
| **Billing** | Stripe subscriptions: a free trial plus three plans, with the trial length, plan names and prices yours to configure rather than hardcoded. Checkout, the customer portal, webhooks, plan changes, and a permission class for gating paid features. |
| **Admin back-office** | A permissioned API over the whole product (user lookup, suspension, subscription and support actions) with roles through Django groups, so support work never means a Django admin login on production. |
| **Core** | The parts every SaaS has and nobody enjoys writing: a waitlist, contact and feedback capture, and the small shared pieces the other apps sit on. |

Each lands as its own app beside `authentication/`, to the same standard: failure paths
tested, rate limits on every route, and a guardrail written down for anything an
assistant would get wrong.

---

## Why this one

**The security decisions are already made, and written down.** A password reset kills
every session including live access tokens. A 6-digit code dies after five wrong
guesses, so the rate limit is not the only thing between an attacker and a million
combinations. Refresh tokens never touch a response body. An unverified account cannot
squat someone else's email address. None of these are obvious, all of them are the kind
of thing you discover after shipping, and each one is pinned by a test that fails if it
is removed.

**The tests cover what goes wrong**, not just what goes right, expired codes, replayed
codes, forged OAuth state, suspended accounts, mass-assignment attempts, and every
message that must not reveal whether an email is registered.

**It stays honest as it grows.** The build fails if a routed view has no rate limit, if
a module declares two views, if a view method has no docstring, or if the OpenAPI
schema emits a single warning. Those guards exist because each one has already caught
something real, and they apply to the apps that have not been written yet.

---

## License

[MIT](LICENSE). Use it commercially, modify it, ship it closed-source. No attribution
in your product required. It is provided as is, with no warranty and no liability:
what you deploy and how you secure it is yours.

Keep the `LICENSE` file if you redistribute the boilerplate itself. If you are building
your own product on it, replace it with whatever licence your product needs.

---

## Found this useful?

**Give it a star**, it costs you a click and it genuinely helps other people find it.

I'm **Yassine**, a backend engineer, and I'm **open to backend work**, Django/DRF/FastAPI
APIs, Stripe and payments, third-party integrations, and taking a prototype the rest
of the way to production.

- Portfolio: **[yassinecodes.dev](https://yassinecodes.dev)**
- Email: **[yassine@yassinecodes.dev](mailto:yassine@yassinecodes.dev)**

Happy to hear about contract work, a full-time role, or just what you ended up
building with this.
