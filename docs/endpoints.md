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
| POST | `/token/refresh/` | cookie | New access token from the cookie |
| POST | `/token/blacklist/` | cookie | Sign out |

`/auth/login/` is the only endpoint that mints a token pair. SimpleJWT's own
`POST /token/` is deliberately not routed: a second door onto the same credentials is a
second place for every rule about them to be forgotten.

The other two live at `/token/` rather than `/auth/` because the refresh cookie is
scoped to that path, the browser only sends it there. Moving them breaks refresh and
logout.

## Administration

Mounted at `/admin/`, beside Django's own admin page rather than under it.

**Reading is staff, writing is superuser.** Support needs to look an account up;
changing one, locking somebody out or deleting them is a different level of trust,
and `is_staff` is a flag this API itself hands out.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/admin/users/` | staff | Every account, cursor paginated, newest first |
| GET | `/admin/users/{user_id}/` | staff | One account in full |
| PATCH | `/admin/users/{user_id}/update/` | superuser | Correct an account on its owner's behalf |
| POST | `/admin/users/{user_id}/suspension/` | superuser | Suspend, with a reason |
| DELETE | `/admin/users/{user_id}/suspension/` | superuser | Reinstate; the record stays |
| DELETE | `/admin/users/{user_id}/delete/` | superuser | Permanent, no undo |
| GET | `/admin/suspensions/` | superuser | Every suspension ever issued |

Every one of these confirms whether an address is registered, which every route under
`/auth/` refuses to do. That is the point of them, and it is why the permission class
has to be right on **every** route in the app rather than most of them.
`config/tests/test_permissions.py` fails the build on any administration view that
does not require at least staff, and `IsSuperUser` subclasses `IsAdminUser` so a
route can only ever be made stricter than that floor, never looser by accident.

**Suspension is a record, not a flag.** Suspending writes a row saying who did it, why
and when, and reinstating closes that row rather than deleting it. An account
suspended and reinstated three times has three rows. `is_suspended` on the account is
the current state; `/admin/suspensions/` is the history.

**Suspension takes effect on the account's very next request**, including one carrying
an access token minted a second earlier, because `authentication/auth.py` reads the
flag on every request rather than trusting the token. Nothing needs revoking. A
suspended account is also refused at `/auth/login/`, so it cannot collect fresh tokens
it would not be able to use.

**Deleting is the only irreversible route here.** It takes the account's suspension
history and its outstanding refresh tokens with it. Suspensions the account *issued*
survive with `suspended_by` set to `null`, so the record of what an operator did
outlives their account. Reach for suspension for anything short of an erasure request.

Not built: an audit trail for the update endpoint, filters on either list, and any
route for revoking sessions, triggering a reset or resending verification on somebody
else's behalf. See [roadmap.md](roadmap.md).

## Development only

| Method | Path | Purpose |
|---|---|---|
| GET | `/docs/` | Swagger UI |
| GET | `/schema/` | The OpenAPI schema |
| GET | `/admin/` | Django admin. Unmatched paths under `/admin/` fall through to it, so a malformed id redirects to its login page rather than answering 404 |

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
