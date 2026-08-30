# Roadmap

What is built, what is planned, and what is left out on purpose.

## Shipped

Authentication, complete and tested: accounts, 6-digit email verification, password
reset and change, Google sign-in, JWT sessions with an httpOnly refresh cookie,
account suspension, per-endpoint rate limits, and a choice of Brevo or Resend for
email. The [readme](../readme.md) has the summary table.

## Next

Nothing below is started. They are the layers most projects reach for after accounts,
in roughly the order people need them:

| | |
|---|---|
| **Billing** | Stripe subscriptions — plans, checkout, customer portal, webhooks, plan changes, and a permission class for gating paid features. |
| **Background jobs** | Celery and a broker, so email and other slow work leave the request cycle. |
| **Admin back-office** | A permissioned API over the domain services — user lookup, suspension, support actions — with roles via Django groups. |
| **File uploads** | S3-compatible object storage with presigned URLs. |
| **Phone verification** | SMS codes. The `phone_number` field is already collected and validated. |

## Deliberately left out

- **A profile-update endpoint.** Which fields are editable is a product decision, and
  the wrong default is worse than none. [The recipe](ai/recipes/add-an-endpoint.md)
  walks through adding one.
- **More social providers.** Google is wired end to end and is the pattern to copy.
- **Docker.** The target platforms build from the repo; see
  [docs/deployment.md](deployment.md).

---

## How to read this

"Next" is a list of what most projects need after accounts, in roughly the order they
need it — not a schedule, and not work in progress. Each one is a self-contained app
you can add yourself; [ai/recipes/add-an-app.md](ai/recipes/add-an-app.md) is the
starting point.
