# Roadmap

What is built, what is coming, what you are expected to add yourself, and what is left
out on purpose.

## Shipped

**Authentication and accounts**, complete and tested: registration, 6-digit email
verification, password reset and change, profile updates, email-address changes,
account deletion, Google sign-in, JWT sessions with an httpOnly refresh cookie, account
suspension, and per-endpoint rate limits.

The parts that are easy to get wrong are the parts that are pinned: codes die after
five wrong guesses, a completed reset signs out every device including live access
tokens, an unverified address cannot be squatted, and no endpoint reveals whether an
email is registered.

**Administration**, the operator's half of accounts: search the user list, read one
account in full, correct one on its owner's behalf, suspend and reinstate with a
reason on record, read every suspension ever issued, and delete an account for good.
Reading is staff, writing is superuser, and a project-level test fails the build on any
route in that app that does not require at least staff.

Suspension is a record rather than a flag: the row says who did it, why and when, and
reinstating closes the row instead of erasing it. Deleting an account is the only
irreversible route in the API and takes its suspension history with it, which is why
the docstring points at suspension for anything short of an erasure request.

**Supporting infrastructure**: Brevo or Resend for email chosen by one variable, Celery
so no email is sent inside a request, four settings modules, CI, pre-commit,
`bootstrap.py`, and the [`ai/`](ai/README.md) rule set.

[endpoints.md](endpoints.md) lists every route; the [readme](../readme.md) has the
summary table.

## Being built next

These are planned work on this repository, each landing as its own app beside
`authentication/` and held to the same standard: failure paths tested, a rate limit on
every route, and a guardrail written down for anything an assistant would get wrong.

No dates. The order below is roughly the order they are needed.

| | |
|---|---|
| **Billing** | Stripe subscriptions: a free trial plus three plans, with the trial length, plan names and prices **yours to configure** rather than hardcoded. Checkout, the customer portal, webhooks, upgrades and downgrades, cancellation, and a permission class for gating paid features. Its figures (MRR, revenue, active plans, trials, conversion) join `/admin/stats/`, which counts only accounts until then. |
| **Admin, the rest of it** | An audit trail, which is the gap: suspension records itself, the update endpoint records nothing, so "who changed this address" has no answer. Then filters on the suspension list (the user list has them), a route onto the existing `revoke_sessions()`, and support actions that trigger the ordinary password-reset and verification emails rather than editing flags by hand. Roles through Django groups, once there is more than one level to express. |
| **Email campaigns** | Superusers sending a provider template to the accounts matching a set of user-list filters, with a test to themselves first and progress while it sends. The shape and what is still open are below. |
| **Core** | The parts every SaaS has and nobody enjoys writing: a waitlist, contact and feedback capture, and the small shared pieces the other apps sit on. |
| **Phone verification** | SMS codes that set `is_phone_verified`. Everything around it is in place: numbers are validated and stored in international form, the flag exists, and the database already allows one verified owner per number. The rules it must follow are below. |

### Phone verification: decided before it is built

- **The SMS provider is pluggable**, an `SMS_PROVIDER` setting with Brevo and Twilio
  behind it, the way `EMAIL_PROVIDER` works. With no API key, a send is skipped and
  logged.
- **Verification is optional and happens after signup.** Registration stays an email
  code only; an account works with `is_phone_verified` false and verifies its number
  later. Google sign-ups, which arrive with no number, are unaffected. A feature that
  needs a proven number, SMS login or two-factor, requires it when it arrives.
- **The latest proof wins.** A correct code for a number verified on another account
  moves ownership: the other account's `is_phone_verified` is cleared and this one's
  set, in one transaction, so there is never a moment with two owners or none. Refusing
  instead would lock people out of their own number, hand recycled numbers to whoever
  held them first for ever, and tell anyone which numbers are registered. Carriers
  reassign numbers; whoever holds the phone today is its owner.
- **Verifying on a new account only removes the number from the old one. It never gives
  access to the old account.** No session, token or reset follows the number. The old
  account is emailed that its number was verified elsewhere and is no longer verified
  on it, so a SIM swap becomes visible rather than silent.
- **The superuser override stays narrower than the code.** An operator proves nothing,
  so `/admin/users/{user_id}/update/` keeps refusing a number verified elsewhere; only
  the code moves ownership. See guardrail 21 in [ai/guardrails.md](ai/guardrails.md).

### Email campaigns: the shape, and what is still open

- **The audience is the user-list filters.** A campaign stores the query parameters,
  and recipients are resolved through `filtered_users()` at send time, the same function
  `/admin/users/` reads, so the people previewed are the people mailed.
- **Draft, test, send, in that order.** Sending is refused until a test has reached the
  sender's own address, the only check that catches a broken template or a wrong
  variable before real users see it. A campaign is a row: the audit trail of who sent
  what to whom, and the key that stops a double click mailing everyone twice.
- **The count is re-checked before sending.** The sender confirms the number they were
  shown; if the filters now match a different number, the send is refused with the new
  figure rather than quietly reaching more or fewer people.
- **A send is claimed once and never retried.** One conditional update moves the
  campaign from tested to sending, so concurrent requests cannot both start it. A
  failed batch is recorded per address and the rest still go out; re-running a half-sent
  campaign would mail everyone before the failure a second time.
- **Open: live progress.** Pusher, which pushes each batch to the dashboard as it lands,
  or the dashboard polling the campaign row, which needs no new service.
- **Open: a marketing opt-out.** A `marketing_opt_out` field that marketing campaigns
  skip. Account mail, verification and security notices, always goes out.

## Add it yourself

Not planned here, because the right answer depends on your product. Each is a
self-contained addition, and the ones with a recipe have the steps written out.

| | |
|---|---|
| **File uploads** | S3-compatible object storage with presigned URLs. |
| **Two-factor authentication** | TOTP, and a "sign out every device" endpoint, the machinery exists (`revoke_sessions`), it just has no route. |
| **Per-account login limits** | The throttles are IP-keyed, so a spray from many addresses against one account is unlimited. [The recipe](ai/recipes/add-an-account-keyed-throttle.md) closes it. |
| **Soft-deleted accounts** | Deletion is a hard delete. [The recipe](ai/recipes/soft-delete-accounts.md) covers retaining records instead, and what it costs. |

[ai/recipes/add-an-app.md](ai/recipes/add-an-app.md) is the starting point for anything
larger.

## Deliberately left out

- **More social providers.** Google is wired end to end and is the pattern to copy.
  Two half-maintained providers are worse than one that works.
- **Docker.** The target platforms build from the repository; see
  [deployment.md](deployment.md).
- **A generic "user settings" table.** What belongs in it is a product decision, and
  the wrong default is harder to remove than to add.
