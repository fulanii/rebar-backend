# Rebar Backend

**The reinforcement inside your SaaS.** Pour whatever product you like on top. The part
underneath that has to hold (accounts, billing, an admin panel, a waitlist) is already
built, already tested, and waiting for you.

Django REST Framework · Python 3.13 · PostgreSQL · Redis · Celery

---

## Why Rebar Backend

**Do not vibe-code your backend.** Ship the product with whatever tools you like. But
the piece holding your users' passwords, sessions and card details is the one piece
where "it looks like it works" is not good enough, and where the mistakes are silent
until the day they are not. This part is written by a backend engineer, deliberately,
not generated and hoped over.

**Your AI agent can extend this without quietly breaking it.** That is the whole point
of how it is built. Every file sits where the pattern says it should, sixteen
guardrails spell out the mistakes an assistant makes here and what each one costs, and
`CLAUDE.md` and `AGENTS.md` hand it those rules the moment it opens the repository. Ask
for a new endpoint and it copies the shape already in front of it. If it takes a
shortcut anyway, the build stops it, because a route with no rate limit or an endpoint
with no documentation fails on its own.

**The decisions you would not know you had to make are already made.** Resetting a
password really does throw an intruder out, on every device, immediately. A stolen
login link cannot be reused. Somebody cannot claim your user's account by signing up
with their email address first. Codes emailed to people expire, and stop working after
five wrong guesses, so nobody can sit there trying a million of them. None of that is
obvious, all of it is the sort of thing you find out after it has gone wrong, and each
one is held in place by a test.

**Finished, not a starting point you still have to finish.** Registration, email
verification, sign-in, password reset, changing an email address, deleting an account,
Google sign-in, and sessions that log out properly. Eighteen endpoints, and 407 tests
that spend most of their effort on the ways it can go wrong rather than the way it goes
right.

**It behaves like a real deployment, not a demo.** Background workers so sending email
never slows a signup, separate settings for development, staging and production,
Brevo or Resend for email, CI, and an API reference generated from the code itself.

---

## Get started

### 📖 [**Read the documentation**](docs/README.md)

Setup, every environment variable, email templates, background jobs, deployment, and
the house rules. Go straight to [getting started](docs/getting-started.md) to run it,
or the [endpoint list](docs/endpoints.md) to see exactly what you get.

---

## What is coming

Billing on Stripe, with a free trial plus three plans whose length, names and prices
are yours to configure. An admin back-office, so support work never means a Django
admin login against production. A core app for the waitlist and the other pieces every
product ends up needing. Each arrives to the same standard as the auth layer. The
[roadmap](docs/roadmap.md) has the detail, including what is deliberately left out.

---

## License

[MIT](LICENSE). Use it commercially, modify it, ship it closed-source, no attribution
required. Provided as is, with no warranty and no liability: what you deploy, and how
you secure it, is yours.

---

## Found this useful?

**Give it a star.** It costs you a click and it genuinely helps other people find it.

I'm **Yassine**, a backend engineer, and I'm **open to backend work**: Django, DRF and
FastAPI APIs, Stripe and payments, third-party integrations, and taking a prototype the
rest of the way to production.

- Portfolio: **[yassinecodes.dev](https://yassinecodes.dev)**
- Email: **[yassine@yassinecodes.dev](mailto:yassine@yassinecodes.dev)**

Happy to hear about contract work, a full-time role, or just what you ended up building
with this.
