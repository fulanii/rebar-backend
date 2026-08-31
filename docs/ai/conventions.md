# Conventions

The house style. Following it is not about taste — it is so that every file in the
codebase can be read the same way, and so an assistant editing one file can infer
how the other forty work.

---

## File layout

One concern per file, grouped in a package, re-exported from `__init__.py`:

```
authentication/views/user_login.py       ← the view lives here
authentication/views/__init__.py         ← exports it
```

When one flow spans several endpoints, it becomes a subpackage — one file per
endpoint, plus `shared.py` for what they have in common:

```
authentication/views/google_auth/
├── __init__.py     ← exports all three views
├── shared.py       ← cache prefixes, TTLs, the redirect helper, the error mixin
├── login.py
├── callback.py
└── exchange.py
```

**One view per file.** A module with two view classes in it is a module to split, and
`config/tests/test_conventions.py` fails the build until you do. Every flow in
`authentication/views/` is a package for this reason: `google_auth/`, `verifications/`,
`jwt_tokens/`, `account_update/`.

A package nests further when it groups several flows rather than several endpoints.
`account_update/` is everything a signed-in person can change about their own account,
so the two flows that need more than one endpoint get a folder each:

```
authentication/views/account_update/
├── update.py           ← name only
├── delete_account.py
├── email/              ← change.py, confirm.py, shared.py
└── password/           ← change.py, reset_request.py, reset_confirm.py, shared.py
```

The `__init__.py` at each level re-exports upward, so `authentication.views` still
offers every view as a flat name and nothing outside the package knows the depth.

Serializers mirror the same shape, so `views/verifications/` has
`serializers/verifications/` beside it. A shape used by more than one feature —
`DetailResponseSerializer`, say — goes in `serializers/common.py` rather than living
in whichever feature happened to need it first.

Because everything is re-exported from the package `__init__.py`, splitting a module
this way changes **no** imports anywhere else — `urls.py` and the other apps never
learn about it. That is the point of importing from the package.

The one thing that does move is a **`patch()` target in a test**: those name a module
path, so `authentication.views.google_oauth.foo` becomes
`authentication.views.google_auth.callback.foo`.

Import from the **package**, never the module:

```python
from authentication.views import UserLoginView      # yes
from authentication.views.user_login import UserLoginView   # no
```

That keeps the file layout an implementation detail you can reorganize later.

---

## Naming

| Thing | Pattern | Example |
|---|---|---|
| Model | Singular noun | `EmailVerification` |
| Serializer | What it is for + `RequestSerializer` / `ResponseSerializer` | `UserLoginRequestSerializer` |
| View | Noun + `View` | `PasswordResetConfirmView` |
| Throttle | Scope + `RateThrottle` | `CodeSubmitRateThrottle` |
| URL name | kebab-case, matching the path | `password-reset-confirm` |
| Test | `test_<what it proves>` | `test_the_code_cannot_be_replayed` |

Test names are sentences. `test_login_2` tells you nothing when it fails at 3am.

---

## Models

- **Text fields are `blank=True` with `default=""`, never `null=True`.** Absent is
  always `""`, so code never has to handle both `None` and `""`. Check with
  `if not user.phone_number:`.
- A field whose purpose is not obvious from its name is named better, or explained
  in `docs/` — not commented. See the comments section below.
- Rules that must *always* hold go in the database (`unique=True`, constraints), not
  only in a serializer. A serializer can be bypassed; the database cannot.

---

## Serializers

- All validation lives here. Views do not validate.
- `validate_<field>` for one field, `validate` for rules spanning two.
- Anything reused goes in `serializers/validators.py`.
- Passwords and codes are `write_only=True`, always.
- Collect multi-part failures into one list rather than reporting them one at a time.

---

## Views

- Thin. Call a serializer, call a util, return a `Response`.
- Always set `permission_classes` and `throttle_classes` explicitly, even when the
  value matches the default, or when a third-party base class already sets one. It
  should never take a search to learn who can call an endpoint or how often.
  `config/tests/test_routes.py` enforces both on every routed view — and the throttle
  one matters beyond tidiness, since `DEFAULT_THROTTLE_CLASSES` is empty and a missing
  `throttle_classes` means no rate limit at all.
- One `@extend_schema` per view, naming the request and response serializers.
- **One tag per view**, `<App>-<Group>` — e.g. `Authentication-Tokens`, the app first
  so a project with several apps groups by app in the Swagger sidebar. A view module
  (or subpackage) holds one tag's worth of endpoints; wanting two tags in one file
  means the file should be split.

---

## Docstrings — the API documentation

The docstring goes on the **HTTP method** (`def post`), not the class, and it is
rendered into the Swagger page. A test fails if a view method has none.

Use Markdown. Sections separated by `---`. Real JSON in the examples, not pseudocode.

```python
def post(self, request):
    """
    One-line summary of what this endpoint does.

    **Endpoint:** POST `auth/example/`

    **Authentication:** None required | JWT required

    **Throttle:** 5/hour per IP (`scope_name` scope)

    ---

    ## Request Body (JSON)

    | Field | Type   | Required | Description                    |
    |-------|--------|----------|--------------------------------|
    | email | string | Yes      | Lowercased and trimmed.        |

    ---

    ## Field Validation Rules

    ### email
    - Required, valid email format.
    - Must not already be registered.

    ---

    ## Responses

    ### 200 OK

    ```json
    {"detail": "Done."}
    ```

    ### 400 Bad Request

    ```json
    {"email": ["Enter a valid email address."]}
    ```

    ---

    ## Post-Request Flow
    1. What happens, in order.
    2. Including anything with a side effect, like sending an email.
    """
```

Document **every** status code the endpoint can return, including 401 and 429. Note
`write_only` fields in the description column. No `:param:` tags — use the tables.

---

## Comments — the code stays clean, the docs carry the reasoning

**This codebase is deliberately almost comment-free.** Explanation lives in `docs/`,
not scattered through the source. Do not add commentary back: a wall of prose above
every line is harder to read than the code, and it goes stale the moment someone
edits the line without editing the paragraph above it.

What is allowed in a `.py` file:

| Allowed | Example |
|---|---|
| A one-line module docstring | describing what the module is for |
| A short docstring where a name cannot carry the meaning | `OneTimeCode`, `issue_code` |
| Section banners in long settings files | `# ---- Database ----` |
| Tool directives | `# noqa: F401`, `# fmt: off` |
| **View HTTP-method docstrings** | the full API documentation, see below |

Everything else goes in `docs/`. If you find yourself wanting to explain a decision,
add it to [guardrails.md](guardrails.md) or [architecture.md](architecture.md) and
leave the code alone.

The one deliberate exception is the **view docstrings**: those are not commentary,
they are the API reference — rendered into the Swagger page and enforced by a test.

---

## Logging

Structured key-value, so logs can be searched:

```python
logger.info("event=login_success email=%s", user.email)
```

Use `%s` placeholders rather than f-strings: the formatting is then skipped entirely
when the level is disabled.

**Never log a password, a token, a verification code, or a full request body.**

---

## Tests

- **Every app owns its tests**, in `<app>/tests/`. There is no project-wide test
  folder. The only exception is `config/tests/`, which holds the schema guards
  because what they check — routing and the docs configuration — belongs to the
  project rather than to any one app.
- Inside an app, mirror the source layout: `tests/models/`, `tests/serializers/`,
  `tests/views/`.
- Add each new app to `testpaths` in `pyproject.toml`, or its tests are never run.
- Group with classes: `class TestLoginFailure:`.
- One behaviour per test. Prefer several small tests to one that asserts eight things.
- Cover the failure paths. A test suite that only tests success proves very little.
- `@pytest.mark.parametrize` for the same assertion over many inputs.
- Never call a real external service. Patch it.
- When a test exists for a security reason, say so in a docstring — otherwise someone
  will eventually delete it as redundant.
