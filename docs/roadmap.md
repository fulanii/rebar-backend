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

**Supporting infrastructure**: Brevo or Resend for email chosen by one variable, Celery
so no email is sent inside a request, four settings modules, CI, pre-commit,
`bootstrap.py`, and the [`ai/`](ai/) rule set.

[endpoints.md](endpoints.md) lists every route; the [readme](../readme.md) has the
summary table.

## Being built next

These are planned work on this repository, each landing as its own app beside
`authentication/` and held to the same standard: failure paths tested, a rate limit on
every route, and a guardrail written down for anything an assistant would get wrong.

No dates. The order below is roughly the order they are needed.

| | |
|---|---|
| **Billing** | Stripe subscriptions: a free trial plus three plans, with the trial length, plan names and prices **yours to configure** rather than hardcoded. Checkout, the customer portal, webhooks, upgrades and downgrades, cancellation, and a permission class for gating paid features. |
| **Admin back-office** | A permissioned API over the whole product (user lookup, suspension, subscription and support actions, audit of who did what) with roles through Django groups. Support work should never mean a Django admin login against production. |
| **Core** | The parts every SaaS has and nobody enjoys writing: a waitlist, contact and feedback capture, and the small shared pieces the other apps sit on. |

## Add it yourself

Not planned here, because the right answer depends on your product. Each is a
self-contained addition, and the ones with a recipe have the steps written out.

| | |
|---|---|
| **File uploads** | S3-compatible object storage with presigned URLs. |
| **Phone verification** | SMS codes. The `phone_number` field is already collected and validated. |
| **Two-factor authentication** | TOTP, and a "sign out every device" endpoint, the machinery exists (`revoke_sessions`), it just has no route. |
| **Per-account login limits** | The throttles are IP-keyed, so a spray from many addresses against one account is unlimited. [The recipe](ai/recipes/add-an-account-keyed-throttle.md) closes it. |
| **Unique phone numbers** | Off by default, because it blocks legitimate shared household numbers. [The recipe](ai/recipes/require-unique-phone-numbers.md). |
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
