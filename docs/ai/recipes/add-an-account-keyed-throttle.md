# Add an account-keyed throttle

**The gap this closes.** Every throttle in `authentication/throttles.py` that guards a
public endpoint subclasses DRF's `AnonRateThrottle`, which buckets by **client IP**.
That stops one machine hammering one endpoint. It does not stop a thousand machines
each trying one password against the same account, from the throttle's point of view
that is a thousand different users each making a single request.

Codes are already covered from the other direction: `MAX_ATTEMPTS` on
`OneTimeCode` counts wrong guesses against the *code*, wherever they came from. There
is no equivalent for `POST auth/login/`, because a password has no row to count on.

**The shape of the fix.** Add a second throttle to the login view, keyed by the email
address in the request body rather than by IP. Both run; either one can return 429.

## 1. The throttle class

`authentication/throttles.py`:

```python
class LoginPerAccountRateThrottle(SimpleRateThrottle):
    scope = "login_account"

    def get_cache_key(self, request, view):
        email = (request.data or {}).get("email", "")

        if not isinstance(email, str) or not email.strip():
            return None

        return self.cache_format % {"scope": self.scope, "ident": email.strip().lower()}
```

Returning `None` means "do not throttle this request", a request with no email in it
has no account to protect, and the IP throttle still applies.

Import `SimpleRateThrottle` from `rest_framework.throttling`.

## 2. The rate

`config/settings/base.py`, in `DEFAULT_THROTTLE_RATES`:

```python
"login_account": "10/hour",
```

Keep it above the IP rate for ordinary use but far below what a spray needs. Ten
failed attempts an hour against one account is generous for a person and useless for
an attacker.

## 3. Wire it up

`authentication/views/user_login.py`:

```python
throttle_classes = [LoginRateThrottle, LoginPerAccountRateThrottle]
```

Do the same on `CustomTokenObtainPairView` in `views/jwt_tokens/obtain.py`, it takes
the same credentials, so leaving it alone leaves the door open.

## 4. Tests

`authentication/tests/views/test_throttling.py` already asserts that every configured
rate has a class and vice versa, so the new scope must appear in that file's `RATES`
map or the suite fails. Add:

- one IP, one account, `limit + 1` attempts → 429
- one IP, **different** accounts each time → not throttled by this class
- different IPs (`REMOTE_ADDR` varied), **same** account → 429, which is the whole point

## What to watch for

- **It counts successes too.** `SimpleRateThrottle` throttles the request, not the
  outcome. Someone signing in ten times an hour legitimately will hit it. If that
  matters, call `throttle.throttle_success()` only on failure by overriding
  `allow_request`, or raise the rate.
- **It is an enumeration surface.** A 429 on an address that has no account tells the
  caller nothing, because the key is the string they sent, not a row that exists.
  Keep it that way, never look the user up to decide whether to count.
- **It needs a shared cache.** Two gunicorn workers with the in-process default each
  keep their own counters, so the effective limit doubles. See guardrail 5.
