# Working on this backend

These docs exist because most changes here will be made by someone working through
an AI tool. That works well when the rules are written down and badly when they are
not: an assistant with no guidance invents a second way to do everything, and six
months later the codebase has four patterns for the same job.

## Reading order

| Read this | When |
|---|---|
| [guardrails.md](guardrails.md) | **First, always.** The mistakes that are easy to make here and what each one breaks. |
| [architecture.md](architecture.md) | Before your first change, to know where things live. |
| [conventions.md](conventions.md) | Before writing code, for the house style. |
| [recipes/](recipes/) | When doing a specific task -- adding an endpoint, a model, an email, an account-keyed throttle. |
| [glossary.md](glossary.md) | Any time a word here is unfamiliar. No prior Django knowledge assumed. |

### The recipes

| Recipe | For |
|---|---|
| [add-an-endpoint.md](recipes/add-an-endpoint.md) | A new route: serializer, view, URL, tests, throttle. |
| [add-a-model.md](recipes/add-a-model.md) | A new table, its migration and its tests. |
| [add-an-app.md](recipes/add-an-app.md) | A whole new app beside `authentication`. |
| [send-an-email.md](recipes/send-an-email.md) | A fifth transactional email. |
| [add-an-account-keyed-throttle.md](recipes/add-an-account-keyed-throttle.md) | Closing the password-spray gap the IP throttles cannot see. |
| [require-unique-phone-numbers.md](recipes/require-unique-phone-numbers.md) | Making `phone_number` unique, and what it costs. |
| [soft-delete-accounts.md](recipes/soft-delete-accounts.md) | Retaining records instead of hard-deleting a user. |

Outside this folder: [../background-jobs.md](../background-jobs.md) covers Celery and
the worker you have to deploy, [../endpoints.md](../endpoints.md) lists every route,
[../configuration.md](../configuration.md) documents every environment variable,
[../email-templates.md](../email-templates.md) covers the four email templates,
[../git-workflow.md](../git-workflow.md) covers branching and pull requests, and
[../deployment.md](../deployment.md) covers shipping.

## If you are not a developer

You can build a real product on this without reading the code, but three things are
worth understanding before you ship to real users, because no assistant will stop
you from getting them wrong:

1. **`.env` holds your secrets.** Never commit it, never paste its contents into a
   chat, never put a real key anywhere else. If one leaks, rotate it. The
   `.example` files are the safe, committed templates — they hold no real values.
2. **Rate limits are load-bearing.** If something is "being blocked" and an
   assistant offers to raise a limit to fix it, that is almost always the wrong fix.
   See [guardrails.md](guardrails.md).
3. **Tests are the safety net.** `pytest` must be green before you deploy. If an
   assistant deletes or skips a failing test rather than fixing the cause, stop and
   ask why the test was failing.

## The one-paragraph summary of what this is

A backend that handles accounts: someone signs up with their name, email, US phone
number and a password; we email them a 6-digit code; entering it activates the
account. They can then sign in, stay signed in, reset a forgotten password, change
their email address, delete their account, or skip all of it and sign in with Google.
Everything else -- billing, your actual product -- is yours to add on top.
