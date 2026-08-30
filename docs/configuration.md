# Configuration

Every setting comes from an environment variable. Nothing sensitive is ever written
into the code.

## How it loads

**The app reads exactly one file: `.env`.** `bootstrap.py` creates it, with a
generated `SECRET_KEY`, from a template it then deletes — so after bootstrap there is
one file per environment and no near-identical copy to edit by mistake.

Which settings module runs is decided by `DJANGO_SETTINGS_MODULE`, and that variable
lives in `.env` like any other:

```
DJANGO_SETTINGS_MODULE=config.settings.dev      # or .staging, or .prod
```

`manage.py`, `wsgi.py` and `asgi.py` each call `load_dotenv()` before Django resolves
the settings module, which is what lets that variable come from the file rather than
having to be exported into every shell. `config/settings/base.py` loads it again for
paths that skip those entrypoints, such as pytest.

To run staging or production settings locally, change that one line — no other file
moves.

### `.env.staging` and `.env.prod`

`bootstrap.py` writes these too, each with its own generated `SECRET_KEY`.
**Neither is ever loaded.**

They are where you keep each environment's real values: the staging database URL, the
production Resend key, and so on. That way you can see at a glance what is in use
where, instead of holding it in your head or digging through a dashboard. When you
deploy, copy from them into your host's environment variables; to run staging settings
locally, copy what you need into `.env`.

All three are gitignored, so none of them can be committed. A separate `SECRET_KEY`
per environment matters: a development key that ends up in a screenshot or a pasted
traceback must not be able to forge a session for a production account.

### Environment variables beat the file

A real environment variable always wins over `.env`. On a host like Railway you set
values in a dashboard and ship no env file at all — better, since nothing sensitive
touches the disk. A missing `.env` is not an error.

---

## Core

### `SECRET_KEY` — required everywhere

Signs session cookies and JWTs. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

**Use a different key in every environment.** Sharing one means a development key
that ends up in a screenshot, a pasted traceback, or a chat log can forge a session
for any production account.

Changing it signs every user out — which is exactly what you want if it ever leaks.
Rotate it immediately in that case.

### `ALLOWED_HOSTS` — required in staging and production

Comma-separated hostnames this app will answer to. Django rejects any request with a
different `Host` header, which stops someone pointing their own domain at your server
and serving your API as if it were theirs.

```
ALLOWED_HOSTS=api.example.com,api2.example.com
```

Development uses `*` and ignores this.

### `CORS_ALLOWED_ORIGINS` — required in staging and production

Comma-separated frontend origins allowed to call this API from a browser. Include the
scheme, include the port if there is one, no trailing slash.

```
CORS_ALLOWED_ORIGINS=https://app.example.com
```

**Never use a wildcard.** This project sends credentials with requests, so allowing
every origin would let any website on the internet make authenticated calls using
your logged-in users' sessions.

Development allows all origins on purpose; that setting is confined to `dev.py`.

### `FRONTEND_URL` — required everywhere

Your frontend's base URL. Google sign-in redirects the browser here when it finishes,
and sends users here on failure too.

### `DOMAIN` — staging and production

Your bare domain, no scheme, no path: `example.com`.

Used to scope the refresh cookie with a leading dot (`.example.com`) so `app.` and
`api.` subdomains share one session. Ignored in development, where browsers reject a
`Domain` attribute on `localhost`.

---

## Database

Leave `DB_NAME` empty in development to use SQLite with no setup at all. All five are
required in staging and production.

| Variable | Notes |
|---|---|
| `DB_NAME` | Database name. Empty in dev means SQLite. |
| `DB_USER` | |
| `DB_PASSWORD` | |
| `DB_HOST` | |
| `DB_PORT` | Defaults to `5432`. |
| `DB_CONN_MAX_AGE` | Seconds to keep a connection open between requests. Defaults to `600`. Opening a new connection over the network is expensive, so reusing one matters. |
| `DB_SSL_MODE` | `require` (default), `verify-full`, or `disable`. Keep encryption on for any remote database — `disable` sends your password in the clear. |

---

## Cache

### `REDIS_URL` — required whenever you run more than one worker

```
REDIS_URL=redis://localhost:6379/0
```

Development defaults to an in-process cache, which is fine for a single-process
`runserver`. It is **not** fine for a real deployment, and the failure is nasty:

The Google sign-in flow writes a short-lived `state` value during one request and
reads it back during another. With several worker processes, each holding its own
in-process cache, those two requests can land on different workers — and the login
fails with `error=google`. Intermittently. On roughly half of attempts. Nothing in
the logs points at the cause.

Rate-limit counters live here too, so without shared Redis each worker enforces its
own separate limits.

---

## Email

Verification codes and password resets go through [Brevo](https://brevo.com) or
[Resend](https://resend.com) — your choice, set by `EMAIL_PROVIDER`.

| Variable | Notes |
|---|---|
| `EMAIL_PROVIDER` | `brevo` (default) or `resend`. |
| `BREVO_API_KEY` | Needed when the provider is `brevo`. |
| `RESEND_API_KEY` | Needed when the provider is `resend`. |
| `VERIFICATION_TEMPLATE_ID` | The template for the signup code. |
| `PASSWORD_RESET_TEMPLATE_ID` | The template for the password-reset code. |
| `EMAIL_CHANGE_TEMPLATE_ID` | The template for the code confirming a new email address. |
| `PASSWORD_CHANGED_TEMPLATE_ID` | The template telling someone their password just changed. |

Without an API key, emails are skipped and logged as a warning.

**Brevo template ids are integers** (`3`), Resend's are strings (`tmpl_abc123`). A
non-numeric id under Brevo is refused with an error rather than sent — which is what
catches a leftover Resend id after switching provider.

**The copy and design of every email live in the provider's dashboard, not in the
code.** The backend sends a template id and its variables — `FIRST_NAME`, `CODE` and
`EXPIRY_MINUTES` for the three that carry a code, `FIRST_NAME` alone for the
password-changed notice — and the provider renders the rest. Changing the wording is a
dashboard edit, not a deploy, and the variable names are identical on both providers,
so switching does not mean rewriting templates.

There is no fallback body: with no template id set, nothing is sent and an error is
logged. **`VERIFICATION_TEMPLATE_ID` is the one that blocks signups** — without it a
new account never receives its code. Building all four takes a few minutes:
[email-templates.md](email-templates.md).

Brevo's free tier allows 300 emails a day across unlimited sending domains; Resend's
allows 100 a day on a single domain. That difference is why Brevo is the default.

Sending never raises: a provider outage is logged and the user's request still
succeeds. A signup should not fail with a 500 because an email service had a bad
minute. The consequence is that you must always give users a way to request the email
again — which is what the resend endpoint is for.

**Reading a code locally without an API key:** the code is hashed in the database
and cannot be read back. Either set a real key, or temporarily log the raw code in
`authentication/views/user_registration.py` and remove that line before committing.
Never log codes in a deployed environment.

---

## Google sign-in

| Variable | Notes |
|---|---|
| `GOOGLE_CLIENT_ID` | From the Google Cloud console. |
| `GOOGLE_CLIENT_SECRET` | Used only in the server-to-server token exchange. |

Setup:

1. In the [Google Cloud console](https://console.cloud.google.com/apis/credentials),
   create an **OAuth client ID** of type **Web application**.
2. Under **Authorized redirect URIs**, add the callback URL for each environment,
   **exactly** — scheme, port and trailing slash included:
   ```
   http://localhost:8000/auth/google/callback/
   https://api.staging.example.com/auth/google/callback/
   https://api.example.com/auth/google/callback/
   ```
   One client can hold several, or you can create a separate client per environment.
3. Copy the client id and secret into the matching env file.

A redirect-URI mismatch is by far the most common reason Google sign-in fails, and
the error Google shows does not make that obvious.

---

## HTTPS

### `SECURE_HSTS_SECONDS` — production only

How long browsers should refuse to talk to your domain over plain http, in seconds.
Defaults to `31536000` (one year), the value required for preload lists.

**Start at `3600` for the first few days.** HSTS is not revocable from the server:
once a browser has seen the header it will refuse http for the full duration, no
matter what you send afterwards. A mistake with a one-year value is a one-year
mistake for everyone who visited during it.

Staging and production also enforce an HTTPS redirect and trust
`X-Forwarded-Proto` from the proxy in front of them. Without that header the redirect
would loop forever behind a load balancer.

---

## Two settings worth knowing about

### `IF_TESTING`

True while the test suite runs (`pytest` imported, or `CI=true`). The environment
modules read it to swap in test-safe behaviour: an in-memory database, no HTTPS
redirect, silent logging. It is why CI can run the whole suite against the *staging*
settings without a real database, a real Redis, or a certificate.

### `NUM_PROXIES`

Set to `1` in `REST_FRAMEWORK`. It tells DRF how many proxies sit in front of the app
when it reads the client IP for rate limiting, by counting back from the end of the
`X-Forwarded-For` header.

Raise it only if you genuinely run more than one proxy. Set it too high and a client
can forge that header to look like a different IP on every request — which makes
every per-IP rate limit in the project useless.

---

## Not configurable by environment variable

These live in `config/settings/base.py` because changing them per environment causes
more problems than it solves:

| Setting | Value | Why |
|---|---|---|
| Access token lifetime | 30 minutes | Short by design. |
| Refresh token lifetime | 7 days | |
| Token rotation + blacklist | On | Turning it off removes real logout. |
| `last_login` on every sign-in | On | `UPDATE_LAST_LOGIN`, plus the two views that issue tokens themselves. |
| Rate limits | Per endpoint | See `DEFAULT_THROTTLE_RATES`. Read `docs/ai/guardrails.md` before changing one. |
| API docs and Django admin | Dev only | Mounted in `config/urls.py` when `ENABLE_API_DOCS` is on, which only `dev.py` sets. |
