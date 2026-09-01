# Getting started

From a fresh clone to a running API and your first deploy. Each step assumes the one
before it worked.

## 1. Clone it and make it yours

```bash
git clone <this repo>
python backend-saas-boilerplate/bootstrap.py my_saas
cd my_saas
```

Run it from *outside* the folder, as above. Renaming the folder is the last thing
`bootstrap.py` does, and a shell sitting inside a folder that gets renamed is left
pointing at a path that no longer exists, staying outside means you simply walk in.
It prints the right `cd` either way.

`bootstrap.py` does everything that makes this yours rather than mine:

- writes `.env`, `.env.staging` and `.env.prod`, each with its own generated
  `SECRET_KEY`, and deletes the `.example` templates they replace
- clears the boilerplate's migrations
- titles the API docs after your project
- gitignores `docs/`, the boilerplate's own documentation, which stays on disk for
  you and your AI tools to read
- deletes this repo's git history, leaving you with no repository at all
- renames the folder to your project name
- deletes itself

It stops short of `git init` on purpose. Starting the repository is step 5, once the
project runs and the tests are green, so your first commit is one you chose to make,
under the git identity you meant to use, of a project you have seen working.

Run it once, before anything else. It cannot run twice, the last thing it does is
remove itself, so what you are left with is your project and nothing of mine.

## 2. Install and run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pre-commit install

python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

Open **http://localhost:8000/docs/**, every endpoint, with its request and response
shapes, generated from the code.

Runs on SQLite with no setup at all.

## 3. Check it works

```bash
pytest
```

Green means the whole flow works on your machine. If it isn't, stop here. Every
step below assumes it is.

## 4. Fill in `.env`

The app runs without any of these; each one switches on a feature.

| To get | Set |
|---|---|
| Emails: verification, password reset, email change, password-changed notice | `EMAIL_PROVIDER` (`brevo` or `resend`), that provider's API key, and the four template ids, see [email-templates.md](email-templates.md) |
| Sign in with Google | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`, see [docs/configuration.md](configuration.md) |

**Nobody can finish registering until `VERIFICATION_TEMPLATE_ID` exists**, since
verification is part of signing up. Build the other three before your first real user.

## 5. Start your repository

`bootstrap.py` deleted the boilerplate's history and did not start a new one, so this
folder is not yet a git repository. Make it yours:

```bash
git init
git add -A && git commit -m "Initial commit"
git branch -M main
git checkout -b staging

# create an empty repo on GitHub, then:
git remote add origin git@github.com:you/my-project.git
git push -u origin main staging
```

Two long-lived branches: `staging` deploys to your staging service, `main` to
production.

**Never commit to either of them directly.** The loop is:

```
branch off staging  →  push the branch  →  pull request  →  merge
                                                              ↓
                    git checkout staging && git pull  ←───────┘
```

CI runs on pull requests **only**, so a direct push to `main` runs no formatter, no
linter, no migration check and no tests, and deploys anyway. Turn on branch
protection for both branches so the rule holds even at 2am.

[docs/git-workflow.md](git-workflow.md) has the commands, the protection
settings, and how to recover if you commit to `main` by accident.
[docs/deployment.md](deployment.md) covers shipping.

## 6. Point your AI tool at the docs

Most tools read [`CLAUDE.md`](../CLAUDE.md) or [`AGENTS.md`](../AGENTS.md) automatically, so
usually there is nothing to do. If yours does not, start a session with:

> Read `CLAUDE.md`, `docs/ai/guardrails.md`, `docs/ai/architecture.md` and
> `docs/ai/conventions.md` before making any changes. Follow the recipes in
> `docs/ai/recipes/` when adding an endpoint, a model or an app.

Read [`ai/guardrails.md`](ai/guardrails.md) yourself too, even if you never
open the code. It is short, and it is the list of things that quietly break this
project, the kind of change an assistant will happily make if you ask it to "just get
the tests passing".

## 7. Start building

Add your own app beside `authentication/`:
[docs/ai/recipes/add-an-app.md](ai/recipes/add-an-app.md).

---

## Day to day

```bash
pytest # the whole suite
pytest authentication -q # one app
black . && isort . && flake8 . # exactly what CI runs
pre-commit install # if you skipped it in step 2
```

CI fails on any formatting difference, lint error, missing migration, or failing test,
so running these locally is how you avoid a red pull request.

With `pre-commit install` done, most of that is automatic: the formatters and linters
run on every commit, and the full suite runs on every push. See
[git-workflow.md](git-workflow.md).

Adding things:

| Task | Guide |
|---|---|
| An endpoint | [ai/recipes/add-an-endpoint.md](ai/recipes/add-an-endpoint.md) |
| A model | [ai/recipes/add-a-model.md](ai/recipes/add-a-model.md) |
| A whole app | [ai/recipes/add-an-app.md](ai/recipes/add-an-app.md) |
| Another email | [ai/recipes/send-an-email.md](ai/recipes/send-an-email.md) |
| Anything else | [ai/recipes/](ai/recipes/) |

---

## Where to go next

Back to the **[documentation index](README.md)**, which routes by what you are trying
to do. The two you will want soonest are
[configuration.md](configuration.md) for the environment variables and
[background-jobs.md](background-jobs.md) before you deploy.
