# Git workflow

Two long-lived branches, and you never commit to either of them directly.

| Branch | Deploys to | Who writes to it |
|---|---|---|
| `main` | production | merged pull requests only |
| `staging` | staging | merged pull requests only |

Everything else is a short-lived feature branch.

## Why not just push to main

**CI does not run on direct pushes.** [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
triggers on `pull_request` into `main` and `staging`, nothing else. Push straight to
`main` and no formatter, linter, migration check or test runs at all, and whatever you
pushed deploys.

Three more reasons, in order of how often they bite:

- **A deploy happens the moment you push.** There is no gap in which to notice the
  mistake. The branch *is* the deployment trigger.
- **Rewriting shared history is painful.** A bad commit on `main` cannot be quietly
  amended, anyone who pulled it has it, and force-pushing a deployed branch breaks
  their clone.
- **A pull request is where review happens**, by a person, by CI, or by an AI tool
  reading the diff. None of that exists on a direct push.

## The loop

```bash
# 1. Start from an up-to-date staging
git checkout staging
git pull

# 2. Branch
git checkout -b feature/password-strength-meter

# 3. Work, committing as you go
git add -A
git commit -m "Add a password strength meter to the register endpoint"

# 4. Check locally what CI will check remotely
black . && isort . && flake8 .    # the hook runs these on every commit
pytest                            # the hook runs this on every push

# 5. Push the branch
git push -u origin feature/password-strength-meter
```

**Step 4 is automatic once you have run `pre-commit install`**, which installs two
hooks at once:

| Gate | Runs | Why there |
|---|---|---|
| **On every commit** | black, isort, flake8, plus hygiene checks (trailing whitespace, unresolved merge conflicts, an accidentally staged private key) | About a second. Cheap enough that you never notice it. |
| **On every push** | the full `pytest` suite | Too slow to sit in front of a commit, fast enough in front of a push, and a push is the last moment before other people see the code. |

Tests are deliberately **not** on the commit hook. Commits are checkpoints: "half a
migration", "before I try the other approach". Blocking those either stops you
committing often, which makes your history worse, or teaches you to reach for
`--no-verify`, which then skips the formatters and the private-key check too. A hook
people bypass is worse than no hook.

The tool versions in `.pre-commit-config.yaml` match the pins in
`requirements-dev.txt` exactly. If they drift, the hook and CI start disagreeing about
the same file, so bump them together.

When black or isort rewrite a file, the commit is aborted with the fixes already
applied: review them, `git add`, and commit again. In a real emergency
`git commit --no-verify` and `git push --no-verify` skip the hooks, and CI then catches
whatever they would have.

If you skipped `pre-commit install`, the two commands above are the whole of it. Run
them before pushing and a red pull request becomes rare.

Then, on GitHub:

```
6. Open a pull request into `staging`
7. CI runs. Fix anything red and push again, the PR updates itself
8. Merge
```

Back on your machine:

```bash
# 9. Move onto the branch you merged into and pull the merge commit
git checkout staging
git pull

# 10. Delete the finished branch
git branch -d feature/password-strength-meter
```

Step 9 matters more than it looks. Your local `staging` does not know about the merge
until you pull it, and branching from a stale `staging` is how you end up reverting
someone else's work in your next pull request.

## Promoting staging to production

Production changes are a pull request from `staging` into `main`, same rule, no
direct pushes:

```bash
git checkout staging && git pull
# open a pull request: staging -> main
```

Nothing should reach `main` that has not sat on `staging` first. That is the whole
point of having two.

## Branch names

Anything readable works. A prefix helps when the list gets long:

```
feature/…    new behaviour
fix/…        a bug
chore/…      dependencies, config, tooling
docs/…       documentation only
```

## Commit messages

Present tense, saying what the change does: `Add rate limiting to the resend endpoint`,
not `added stuff`. The next person reading `git log` is usually you, six months later,
trying to work out when something changed.

## Enforcing it

Ask an assistant nicely and it will still occasionally commit to whatever branch is
checked out. Make it impossible instead, in GitHub, under **Settings → Branches**,
add a protection rule for `main` and `staging`:

- **Require a pull request before merging**
- **Require status checks to pass**, select the CI job
- **Do not allow bypassing the above settings**, so the rule applies to you too

That last one is the one people skip, and it is the one that matters: a rule you can
bypass at 2am is not a rule.

## If you already committed to main by mistake

Nothing is broken yet if you have not pushed:

```bash
git branch feature/my-work        # keep the commits on a new branch
git reset --hard origin/main      # put main back where the remote has it
git checkout feature/my-work
```

If you already pushed, do **not** force-push a branch other people have. Open a pull
request that reverts it, and let that go through the normal loop.
