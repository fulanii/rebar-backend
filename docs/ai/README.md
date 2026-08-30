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
| [recipes/](recipes/) | When doing a specific task -- adding an endpoint, a model, an email. |
| [glossary.md](glossary.md) | Any time a word here is unfamiliar. No prior Django knowledge assumed. |

Outside this folder: [../configuration.md](../configuration.md) documents every
environment variable, [../git-workflow.md](../git-workflow.md) covers branching and
pull requests, and [../deployment.md](../deployment.md) covers shipping.

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
account. They can then sign in, stay signed in, reset a forgotten password, or skip
all of it and sign in with Google. Everything else -- billing, your actual product --
is yours to add on top.
