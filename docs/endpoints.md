# The endpoints

Every route the backend serves. Full request and response documentation for each
(fields, validation rules, every status code, worked examples) is on the Swagger page
at **`/docs/`**, generated from the docstring on each view, so it cannot drift from
the code.

## Accounts

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register/` | None | Create an account; emails a 6-digit code |
| GET | `/auth/me/` | JWT | The signed-in user's profile |
| POST | `/auth/change-email/` | JWT | Email a code to a new address |
| POST | `/auth/change-email/confirm/` | JWT | Code → the account moves to that address |
| POST | `/auth/delete-account/` | JWT | Permanently delete your own account |

## Email verification

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/verify-email/` | None | Submit the code; activates the account |
| POST | `/auth/resend-verification/` | None | New code; invalidates the previous one |

## Passwords

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/password-reset/` | None | Email a reset code |
| POST | `/auth/password-reset/confirm/` | None | Code + new password; signs out every device |
| POST | `/auth/change-password/` | JWT | Change password while signed in |

## Google sign-in

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/auth/google/login/` | None | Start Google sign-in (navigate, don't fetch) |
| GET | `/auth/google/callback/` | None | Google returns here |
| POST | `/auth/google/exchange/` | None | Handoff code → tokens |

The first two are reached by **full-page navigation**, not `fetch`. They respond with
redirects, including on error, a JSON error body would render as raw text in the
address bar.

## Sessions

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/login/` | None | Access token + profile, refresh cookie set |
| POST | `/token/` | None | Standard SimpleJWT token pair; only use `/auth/login/` |
| POST | `/token/refresh/` | cookie | New access token from the cookie |
| POST | `/token/blacklist/` | cookie | Sign out |

These four live at `/token/` rather than `/auth/` because the refresh cookie is scoped
to that path, the browser only sends it there. Moving them breaks refresh and logout.

## Development only

| Method | Path | Purpose |
|---|---|---|
| GET | `/docs/` | Swagger UI |
| GET | `/schema/` | The OpenAPI schema |
| GET | `/admin/` | Django admin |

All three are mounted only when `ENABLE_API_DOCS` is on, which is the `dev` settings
module and nothing else. They 404 in staging and production.

---

## What every response looks like

**Access tokens** come back in the JSON body. **Refresh tokens never do**: they are
set as an httpOnly cookie scoped to `/token/`, so JavaScript cannot read one and a
cross-site scripting bug in your frontend cannot steal a week-long session.

Errors are either a single `detail` string or one entry per invalid field:

```json
{ "detail": "Invalid or expired verification code." }
```

```json
{ "email": ["An account with this email already exists."] }
```

Endpoints that take an email address return the **same** message whether or not the
address is registered, so none of them can be used to find out who has an account
here. See [ai/guardrails.md](ai/guardrails.md).

Every endpoint is rate limited and can return **429** with a `detail` saying when to
try again. The two Google routes reached by browser navigation redirect to
`FRONTEND_URL/login?error=google_rate_limit` instead, since a JSON error body would
render as raw text in the address bar.
