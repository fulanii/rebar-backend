# Glossary

Plain-English definitions of every term used in these docs and in the code. No prior
backend experience assumed.

---

### API
The set of URLs your frontend (or anyone else) can call to make something happen.
This whole project is an API: it has no pages, only endpoints that take JSON and
return JSON.

### Endpoint
One URL that does one thing, e.g. `POST /auth/login/`. The method (`GET`, `POST`)
is part of its identity: `GET /auth/me/` and `POST /auth/me/` are different endpoints.

### JSON
The text format APIs use to exchange data: `{"email": "jane@example.com"}`.

### Model
A Python class describing one kind of thing you store — a user, a verification code.
Each model becomes a database table, and each of its fields becomes a column.

### Migration
A file recording a change to the database's shape ("add a phone_number column").
Django generates them from your models with `makemigrations` and applies them with
`migrate`. **Never edit one that has already been applied** — write a new one.

### Serializer
The translator and the bouncer. Turns incoming JSON into validated Python (rejecting
anything that breaks the rules) and turns Python back into JSON on the way out.

### View
The code that handles one endpoint. In this project views are deliberately thin:
they call a serializer, do one thing, and return a response.

### Middleware
Code that runs on every request, before and after your view. This project uses one,
to log each request.

---

### Authentication vs authorization
**Authentication** is *who are you* — checking the token and finding the user.
**Authorization** is *what may you do* — checking permissions. Different questions;
this codebase keeps them in different files (`auth.py` and `permission_classes`).

### JWT (JSON Web Token)
A signed string that proves who you are. The server can verify it without looking
anything up, because it is signed with `SECRET_KEY`. Anyone can *read* what is inside
one — it is not encrypted — so it must never contain a secret.

### Access token
The short-lived JWT (30 minutes here) sent with every request as
`Authorization: Bearer <token>`. Short-lived on purpose: a stolen one expires soon.

### Refresh token
The long-lived token (7 days) used only to obtain new access tokens. In this project
it never appears in a response body — it lives in an httpOnly cookie.

### Token rotation
Each time a refresh token is used, it is replaced with a new one and the old one is
blacklisted. So a stolen refresh token stops working as soon as the real user
refreshes — which limits the damage to a single use.

### Blacklist
The list of refresh tokens that have been revoked. What makes logout real: without
it, clearing the cookie only removes the browser's copy while the token itself stays
valid.

### httpOnly cookie
A cookie the browser will not let JavaScript read. It is still sent with requests
automatically — the browser can use it, your code cannot. That is what protects the
refresh token from a script injected into your frontend.

### SameSite
A cookie setting controlling whether the cookie is sent on requests coming from
other sites. `Lax` blocks it on cross-site form posts, which blunts a class of attack
where another site tricks a logged-in user's browser into acting on their behalf.

### CORS (Cross-Origin Resource Sharing)
Browser rules about which websites may call your API. Your frontend runs on a
different origin from your API, so its origin has to be allowed explicitly. Allowing
*every* origin, with credentials enabled, means any website can make authenticated
calls using your users' sessions.

### CSRF (Cross-Site Request Forgery)
An attack where another site causes a logged-in user's browser to make a request to
your API without them meaning to. The `state` value in the Google login flow is the
same idea applied to OAuth.

---

### Hashing
A one-way scramble. A password (or a verification code) is stored as a hash, so a
leaked database does not hand over the originals — you can check a guess against a
hash, but you cannot turn a hash back into the password.

### Salt
Random data mixed into each hash so that two people with the same password get
different stored values. Django does this for you.

### OTP / one-time code
The 6-digit number emailed to verify an address or reset a password. Single-use, and
expires after 15 minutes.

### OAuth
The protocol behind "Sign in with Google". Google confirms who the user is and tells
us, so we never see their Google password.

### Throttle / rate limit
A cap on how often something can be called — 5 per hour, 60 per minute. It is the
main defence against guessing codes and passwords.

---

### Environment variable
A setting passed to the app from outside the code, so secrets never get committed.
Kept in `.env` locally; set in your hosting dashboard in production.

### `.env`
The single file holding your secrets, gitignored. It also carries
`DJANGO_SETTINGS_MODULE`, which decides whether the dev, staging or production
settings run. Never commit it, never paste it into a chat.

`.env.staging` and `.env.prod` sit beside it holding each environment's values. Neither
is ever loaded — they are reference, and what you copy from when deploying.

### Settings module
Which configuration file the app loads: `config.settings.dev` on your machine,
`config.settings.prod` in production.

### Fixture
A reusable piece of test setup. `base_user` creates a user for any test that asks for
one by naming it as an argument.

### Mock / patch
Replacing a real thing with a fake during a test — the email sender, for instance —
so tests never send real email and never depend on a third party being up.

### Migration vs. fixture vs. seed
A *migration* changes the database's shape. A *fixture* is test setup. *Seeding* is
inserting starter data. They are three different jobs.
