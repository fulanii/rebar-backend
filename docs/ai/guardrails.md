# Guardrails

The mistakes that are easy to make in this codebase, why they are tempting, and what
each one actually breaks. Most of them leave the tests green and the app apparently
working, which is exactly what makes them worth writing down.

---

## 1. Never put the refresh token in a response body

**The temptation:** the client needs the token, so return it. It is right there in
the dict.

**What it breaks:** the refresh token is a seven-day session. In the httpOnly cookie
it is unreachable from JavaScript, so a script injected into your frontend cannot
steal it. Put it in the body and the frontend has to store it somewhere JavaScript
*can* read — and now one cross-site scripting bug hands an attacker a week of
access to every account.

**Do this instead:** `set_refresh_cookie(response, refresh)` from
`authentication/utils/cookies.py`. Return only `access`.

---

## 2. Never raise or remove a rate limit to make something work

**The temptation:** you hit a 429 while testing and it is in the way. The fastest fix
is to change `5/hour` to `500/hour`.

**What it breaks:** the limit on `code_submit` is most of what makes a 6-digit code
safe. A million combinations at five attempts an hour is not an attack anyone can run.
At five hundred an hour it is a few days of scripted guessing, unattended, against
every account.

The throttles are keyed by IP, so they are only half the story. The other half is
`MAX_ATTEMPTS` on the code itself (`authentication/models/one_time_code.py`): five
wrong guesses burn the code no matter how many addresses they came from, and the user
requests a new one. Removing that counter re-opens the door the throttle cannot close.

**Do this instead:** in tests, the cache is cleared between tests automatically —
if you are hitting a limit, you are probably making more requests in one test than
the endpoint expects. A test of something sitting *behind* the throttle can take the
`unlimited_requests` fixture, which lifts the limits for that test only. In manual
testing, restart the server or clear the cache.

**And when adding a view, give it a throttle.** `DEFAULT_THROTTLE_CLASSES` is empty on
purpose, so a view that omits `throttle_classes` is not rate limited at all — it fails
open, silently, with nothing in the logs. `config/tests/test_routes.py` walks the
URLconf and fails on any routed view without one.

---

## 3. Do not change the refresh cookie's path or name

**The temptation:** `/token/` looks arbitrary, and moving the token endpoints under
`/auth/` would be tidier.

**What it breaks:** browsers only send a cookie to URLs under its path. Move the
endpoints without moving the cookie and refresh silently stops working — users get
signed out an hour later with no error anywhere. Worse, deleting a cookie requires
the *exact* same name, path and domain used to set it: a mismatch deletes nothing,
so logout appears to succeed while the session stays alive.

**Do this instead:** `REFRESH_COOKIE_PATH` in `authentication/utils/cookies.py` is
the single source of truth, and the token routes in `config/urls.py` must stay under
it. Change both together or neither.

---

## 4. Do not let authentication endpoints reveal who is registered

**The temptation:** "No account with that email" is a genuinely more helpful error
than "Incorrect email or password."

**What it breaks:** it turns the login form into a tool for checking whether any
given address has an account here. That list is the first thing anyone planning a
credential-stuffing or phishing campaign wants.

**Do this instead:** wrong password, unknown address, expired code, used code and a
code that has run out of attempts all return the **same** message. Password reset and
resend-verification return 200 for addresses that do not exist. There are tests
asserting exactly this; if you change a message, run them.

The one deliberate exception: an unverified account is told to verify — but only
after its password has been confirmed correct, so it cannot be used to probe.

---

## 5. Multi-process deployments need Redis

**The temptation:** the default in-process cache works fine locally, so why configure
anything.

**What it breaks:** the Google OAuth flow writes a `state` value in one request and
reads it back in another. With more than one worker process, those two requests can
land on different workers with different in-process caches, and the login fails with
"error=google". Intermittently. On maybe half of attempts. This is genuinely hard to
diagnose from the symptom.

**Do this instead:** set `REDIS_URL`. `staging.py` and `prod.py` already use it.

---

## 6. Never edit a migration that has already been applied

**The temptation:** the migration has a mistake in it, so fix the mistake.

**What it breaks:** Django records which migrations have run. Editing an applied one
does not re-run it — your database keeps the old shape while the file claims the new
one, and the two drift apart silently until a query fails in production.

**Do this instead:** change the model, then `python manage.py makemigrations` to
generate a *new* migration.

---

## 7. Keep secrets out of code — including out of docstrings

**The temptation:** a docstring example reads better with a real-looking key in it,
and it is only documentation.

**What it breaks:** documentation is committed, pushed, and indexed like everything
else. Secret-scanning bots watch public repositories for exactly this.

**Do this instead:** secrets go in `.env`, which is gitignored. The committed
`.example` files list the names with empty values. Use obvious placeholders in
examples.

Related: use a **different** `SECRET_KEY` in each environment. Sharing one means a
development key pasted into a chat or a screenshot also forges production sessions.

---

## 8. Do not delete or skip a failing test to get to green

**The temptation:** the test is in the way and the feature works when you try it by
hand.

**What it breaks:** the tests here mostly encode security properties — that a token
is invalidated, that an error does not leak, that a code cannot be replayed. A test
failing after your change usually means your change broke one of those.

**Do this instead:** read what the test asserts and why. If the behaviour genuinely
should change, change the test deliberately and say so.

---

## 9. Validation belongs in serializers, not views

**The temptation:** it is one `if` statement and the view is right there.

**What it breaks:** the rule now applies to one endpoint instead of to the field.
This is how password reset ends up accepting passwords that registration rejects.

**Do this instead:** put it in the serializer. If two serializers need it, put it in
`authentication/serializers/validators.py`.

---

## 10. Do not widen CORS or ALLOWED_HOSTS in staging or production

**The temptation:** you are getting a CORS error and `CORS_ALLOW_ALL_ORIGINS = True`
makes it stop.

**What it breaks:** with `CORS_ALLOW_CREDENTIALS` also on, it lets *any* website make
authenticated requests to your API using your users' cookies.

**Do this instead:** add your frontend's exact origin to `CORS_ALLOWED_ORIGINS` in
the environment. The wide-open setting is confined to `dev.py` on purpose.

---

## 11. Never adopt an unverified account without discarding its password

**The temptation:** a Google sign-in arrives for an address that already has a row.
The obvious move is to activate it and let the person in — same email, same person.

**What it breaks:** for an *unverified* row, nobody ever proved they own that address,
so nobody proved they set that password. This is the pre-hijacking attack:

1. An attacker registers the victim's address with a password they choose. The row
   exists, inactive and unverified; they cannot verify it, because the code went to
   the victim.
2. The victim later signs in with Google. The row is adopted and activated.
3. The attacker's password still works. They now hold a live, verified account
   belonging to someone else, and the victim sees nothing wrong.

**Do this instead:** when adopting a row that was never verified, call
`set_unusable_password()` and set `auth_provider` to the identity provider. The person
keeps their account and can set a password through the reset flow, which is the same
proof of ownership they skipped.

An account that *was* already verified keeps its password — that user did prove
ownership, and a social login should be a second way in, not a lockout.

The same reasoning runs the other way at registration. An unverified row cannot hold
an address hostage either: registering with an address that has one **takes it over**,
overwriting every field, discarding the old password and emailing a fresh code. Without
that, anyone could permanently lock a person out of your product by registering their
email and never verifying it. A **verified** address is still rejected.

`authentication/utils/google_oauth.py` and
`authentication/serializers/user_registration.py` do this, and both are pinned by
tests.

---

## 12. A password reset must end every other session

**The temptation:** the reset endpoint sets a new password and returns 200. Job done.

**What it breaks:** a reset usually means *someone else is in the account*. Their
refresh token is good for seven days and knows nothing about the new password, so
rotating it changes nothing for them. The user believes they have locked the intruder
out. They have not.

**Do this instead:** call `revoke_sessions(user)` from `authentication/utils/` in the
same transaction. It does two things, because the two token types are stored
differently:

- **Refresh tokens** are rows, so they are blacklisted.
- **Access tokens** are stored nowhere at all, so the user row is stamped with
  `sessions_revoked_at` and `authentication/auth.py` refuses any token whose `iat` is
  at or before it. Without that stamp the intruder keeps working for up to 30 more
  minutes — most of a reset's value, gone.

Never delete the `sessions_revoked_at` check to fix a test. A test that fails on it is
usually issuing a token and revoking in the same second, which the check refuses on
purpose; move the stamp, not the check.

Password *change* deliberately does not revoke: that user is signed in and gave the
current password, so the other sessions are theirs. Both paths do email a
notification, which is how a change nobody made becomes visible.

---

## 13. Changing the login address needs the password, and a code to the new one

**The temptation:** the request is authenticated, so take `new_email` and save it.

**What it breaks:** two different things, and both are fatal.

Skipping the **password** means a stolen access token can move the account to an
address the attacker controls — and then reset the password at leisure. Thirty
minutes of stolen token becomes permanent ownership.

Skipping the **code to the new address** means the account can be moved to an address
nobody has proved they own. That is a typo away from locking a real user out of their
own account, and one deliberate keystroke away from parking your users on a domain
someone else controls.

**Do this instead:** what `authentication/views/account_update/email/` does. The password is
required even though the request is authenticated; a code goes to the new address and
**only** the new address; and availability is checked twice — once when the code is
issued and again when it is used, because minutes pass in between.

Google accounts are refused outright: they have no password to confirm, and moving the
address would break the link to the Google identity that signs them in.

---

## 14. Queued email needs a worker, and a worker is a second deployment

**The temptation:** `CELERY_BROKER_URL` is set, the tests pass, registration returns
201. Ship it.

**What it breaks:** nothing visible. The endpoint queues the email and returns
successfully; if no worker is running, that job sits in Redis forever. Users register
and no code ever arrives. The web logs show 201s. Every test still passes, because the
suite runs tasks eagerly and never needs a broker at all.

**Do this instead:** deploy the worker as its own service —
`celery -A config worker --loglevel=info` — with the same environment variables as the
web service, and check its startup log lists the task:

```
[tasks]
  . authentication.tasks.send_email
```

Development has no such trap: with `CELERY_BROKER_URL` empty, jobs run inline in the
request. Staging and production refuse to boot without a broker rather than quietly
doing the same, because inline sending in production is a latency bug that only shows
up under load.

---

## 15. A task takes ids, not objects

**The temptation:** the task needs the user, and the user is right there.

**What it breaks:** two things. Task arguments are serialized to JSON, so a model
instance cannot cross to the worker at all — it fails at queue time, in production,
having passed every test where eager mode kept it in the same process. And if you
serialize the fields by hand instead, the worker acts on a snapshot that may be
seconds stale.

**Do this instead:** pass `user.id` and refetch inside the task. Assume the task runs
**twice** — a queue delivers at least once — and never log a code, a token or a
password from one.

---

## 16. `is_active` is not a spare field

It means "has verified their email". Registration deliberately creates users with
`is_active=False`, and Django's own auth refuses to authenticate them. Repurposing it
for something else in your product silently lets unverified accounts sign in.
