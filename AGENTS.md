# Agent instructions

**Read [CLAUDE.md](CLAUDE.md) first.** It is the single source of truth for how to
work in this repository, and this file exists only so tools that look for
`AGENTS.md` find their way there. Do not duplicate guidance here -- two copies drift,
and then they contradict each other.

Then read, in order:

1. [docs/ai/guardrails.md](docs/ai/guardrails.md) — the mistakes that are easy to
   make here and what each one breaks. Short. Read it before your first change.
2. [docs/ai/architecture.md](docs/ai/architecture.md) — how a request flows and
   where every kind of file belongs.
3. [docs/ai/conventions.md](docs/ai/conventions.md) — the house style, with examples.
4. [docs/ai/recipes/](docs/ai/recipes/) — step-by-step guides for common tasks.

New to Django or to backends? [docs/ai/glossary.md](docs/ai/glossary.md) explains
every term used above in plain English.

## The very short version

- Run `pytest` and `black . && isort . && flake8 .` before claiming you are done.
- The refresh token never appears in a response body -- only in the httpOnly cookie.
- Never lower a rate limit, or drop a code's attempt counter, to make a test pass.
- A completed password reset revokes every session — refresh tokens *and* live
  access tokens — via `revoke_sessions()`. A password change deliberately does not.
- Every view method needs a docstring; a test enforces it.
- Secrets live in `.env`, never in code.
- Do not add explanatory comments — reasoning goes in `docs/`, not above the line.
- Never commit or push to `main` or `staging`. Branch, push, open a pull request.
