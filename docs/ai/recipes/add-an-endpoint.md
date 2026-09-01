# Recipe: add an endpoint

Worked example: `GET /auth/sessions/`, listing the caller's active sessions. Adapt
the names; the order of the steps is the part that matters.

Touch the files in this order, each step depends on the one before.

---

## 1. The serializer, `authentication/serializers/sessions.py`

Decide the shape of what goes in and what comes out. All validation lives here.

```python
from rest_framework import serializers


class SessionResponseSerializer(serializers.Serializer):
    """One active session."""

    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
```

Export it from `authentication/serializers/__init__.py`, and add it to `__all__`.

If a field rule is shared with another serializer, put it in
`serializers/validators.py` instead of duplicating it.

---

## 2. The throttle, only if you need a new limit

Reuse an existing scope where one fits. If not, add the rate to
`config/settings/base.py`:

```python
"DEFAULT_THROTTLE_RATES": {
    ...
    "sessions": "60/minute",
}
```

and a class in `authentication/throttles.py`:

```python
class SessionsRateThrottle(UserRateThrottle):
    """`60/minute`, read-only, called on page load."""

    scope = "sessions"
```

`UserRateThrottle` counts per account; `AnonRateThrottle` counts per IP and is what
unauthenticated endpoints need. **Adding the rate without using the class does
nothing at all.**

---

## 3. The view, `authentication/views/sessions.py`

Thin: call the serializer, do the one thing, return a response. The docstring is the
API documentation and a test enforces its presence, copy the template from
[../conventions.md](../conventions.md) and fill in every status code the endpoint can
return, 401 and 429 included.

```python
@extend_schema(
    tags=["Authentication-Accounts"],
    summary="List active sessions",
    responses={200: SessionResponseSerializer(many=True)},
)
class SessionListView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionsRateThrottle]

    def get(self, request):
        """
        The signed-in user's active sessions.

        **Endpoint:** GET `auth/sessions/`

        **Authentication:** JWT required

        **Throttle:** 60/minute per user (`sessions` scope)

        ---

        ## Responses

        ### 200 OK

        ```json
        [{"created_at": "2026-08-29T10:00:00Z", "expires_at": "2026-09-05T10:00:00Z"}]
        ```

        ### 401 Unauthorized

        ```json
        {"detail": "Authentication credentials were not provided."}
        ```
        """
        ...
```

Always set `permission_classes` and `throttle_classes` explicitly, even when they
match the default. Export the view from `authentication/views/__init__.py`.

**Pick the right tag.** It decides which group the endpoint appears under in the
Swagger sidebar:

| Tag | For |
|---|---|
| `Authentication-Accounts` | Creating an account, reading a profile |
| `Authentication-Verifications` | Email verification codes |
| `Authentication-Tokens` | Sign in, refresh, sign out |
| `Authentication-Passwords` | Reset and change password |
| `Authentication-Google` | The Google OAuth flow |

Adding a new group means adding it to `TAGS` in `config/settings/base.py` too,
otherwise it still appears, but unordered and without a description.

---

## 4. The route, `authentication/urls.py`

```python
path("sessions/", SessionListView.as_view(), name="sessions"),
```

The `name` is what `reverse("sessions")` resolves, in tests and in redirects. Tests
should use `reverse()` rather than a hardcoded path, so moving a URL does not break
them.

---

## 5. The tests, `authentication/tests/views/test_sessions.py`

Cover the failure paths, not just the success. At minimum:

```python
class TestSessionList:
    def test_returns_the_users_sessions(self, auth_client):
        ...

    def test_requires_authentication(self, api_client):
        assert api_client.get(reverse("sessions")).status_code == 401

    def test_does_not_return_another_users_sessions(self, auth_client, second_user):
        """Per-user isolation. The bug this catches is a serious one."""
        ...
```

Fixtures available from `conftest.py`: `api_client`, `auth_client`, `base_user`,
`second_user`, `unverified_user`, `user_password`, `block_outbound_email`,
`unlimited_requests` (lifts the rate limits for one test, only for testing something
that sits behind a throttle).

---

## 6. Check it

```bash
pytest
black . && isort . && flake8 .
python manage.py runserver   # then http://localhost:8000/docs/
```

Your endpoint should appear in the Swagger page with its documentation. If it does
not, the `@extend_schema` decorator or the route is wrong.

---

## If the endpoint needs a new model

Do [add-a-model.md](add-a-model.md) first, the serializer needs something to
serialize.
