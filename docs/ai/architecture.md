# Architecture

## The shape of the thing

One Django project (`config`) and one app (`authentication`). Your product code will
be new apps beside it.

```
HTTP request
    │
    ▼
config/middleware.py         logs the request
    │
    ▼
config/urls.py               matches the path, hands off to an app's urls.py
    │
    ▼
authentication/urls.py       matches the rest of the path, names a view
    │
    ▼
authentication/auth.py       who is this? (JWT + suspension check)
    │
    ▼
authentication/throttles.py  have they done this too often?
    │
    ▼
authentication/views/…       the endpoint
    │
    ├──▶ serializers/…       validate input, shape output
    ├──▶ models/…            read and write the database
    └──▶ utils/…             cookies, emails, codes, Google
    │
    ▼
HTTP response
```

The order matters: authentication and throttling both run **before** your view code.
A view can assume `request.user` is a real, active, unsuspended user whenever its
`permission_classes` say `IsAuthenticated`.

## What each layer is for

| Layer | Job | Does not |
|---|---|---|
| `models/` | Define the data and rules that are always true of it. | Talk HTTP. Know about requests. |
| `serializers/` | Validate incoming JSON; decide what goes back out. | Query across the app. Send email. |
| `views/` | Handle one endpoint: call a serializer, call a util, return a response. | Contain validation logic. |
| `utils/` | Reusable pieces with no HTTP knowledge: hashing a code, setting a cookie. | Import views. |
| `throttles.py` | One class per rate limit scope. | Anything else. |
| `auth.py` | Decide who the caller is. | Decide what they may do. |

**Validation belongs in serializers, not views.** A view that checks a field itself
is a rule that will not apply the next time that field is accepted somewhere else.
`serializers/validators.py` holds the rules shared by more than one serializer --
password strength lives there so registration and password reset cannot disagree.

## Dependency direction

```
views  ──▶  serializers  ──▶  models
   └────▶  utils  ────────────▶  models
```

Arrows only point right. `models` imports nothing from `serializers` or `views`;
`utils` imports nothing from `views`. Breaking this gives you circular imports, which
surface as baffling errors at startup rather than where the mistake is.

When you add a second app, it must **not** import from `authentication` internals.
Get the user model with `get_user_model()` or `settings.AUTH_USER_MODEL`.

## Tests

Each app owns its tests in `<app>/tests/`, mirroring the source layout. There is no
project-wide test folder; `config/tests/` holds only the schema guards, because what
they check — the routing table and the API-docs configuration — belongs to the project
rather than to any one app.

Shared fixtures live in the root `conftest.py` and are available to every app without
being imported. App-specific ones go in `<app>/tests/conftest.py`.

New apps must be added to `testpaths` in `pyproject.toml` or their tests never run.

## Settings

Four files in `config/settings/`. Each environment module starts with
`from .base import *` and then changes only what differs.

| Module | Used for | Notable |
|---|---|---|
| `base.py` | Shared by all. | Apps, DRF config, JWT lifetimes, throttle rates, logging. |
| `dev.py` | Your machine. | `DEBUG=True`, SQLite with no setup, CORS wide open, **the API docs and Django admin are mounted here and nowhere else**. |
| `staging.py` | A production rehearsal. | Postgres, Redis, HTTPS enforced. CI runs the tests against this. |
| `prod.py` | Real traffic. | Same as staging plus HSTS. Missing env vars fail loudly at boot. |

Pick one with `DJANGO_SETTINGS_MODULE`. It defaults to `config.settings.dev`.

## Authentication, end to end

Two tokens, and the difference matters:

- **Access token** — 30 minutes. Sent by the client as `Authorization: Bearer …`.
  Returned in the JSON body. If stolen it is useful for at most 30 minutes.
- **Refresh token** — 7 days. Exchanged for new access tokens. **Never appears in a
  response body.** It lives in an httpOnly cookie scoped to `/token/`, so JavaScript
  cannot read it, and so it is not attached to ordinary API calls.

Rotation is on: every refresh issues a new refresh token and blacklists the old one.
A stolen refresh token therefore stops working as soon as the real user refreshes.

Suspension is checked in `authentication/auth.py`, on **every** request, because a
JWT is stateless and would otherwise stay valid for its full 30 minutes after you
suspend someone.

## Where state lives

| Where | What | Survives a restart? |
|---|---|---|
| Database | Users, verification codes, reset codes, blacklisted tokens. | Yes |
| Cache | Rate-limit counters; the Google OAuth `state` and handoff code. | No |
| Nowhere | Access tokens. They are self-describing and are not stored. | — |

The cache entries are why a multi-process deployment needs Redis rather than the
in-process default: two workers must see the same cache or Google logins fail at
random. See [guardrails.md](guardrails.md).
