# Background jobs

Slow work does not belong in an HTTP request. Sending an email means a round trip to
Brevo or Resend, usually a few hundred milliseconds, occasionally many seconds, and
sometimes never. A signup that waits for it is a signup that is as slow as the worst
day your email provider is having.

Celery moves that work to a separate process. The request writes a job to a queue and
returns; a **worker** picks it up and does the sending.

```
POST /auth/register/          worker
   │                             │
   ├─ create the account         │
   ├─ generate the code          │
   ├─ queue "send this email" ──▶├─ call Brevo
   └─ 201 Created                ├─ failed? retry, backing off
      (does not wait)            └─ done
```

## What is queued today

Only email. All four templates go through one task,
[`authentication/tasks/send_email.py`](../authentication/tasks/send_email.py) → `send_email`.

Nothing else in this project is slow enough to be worth queueing. Resist the urge to
queue things that are fast: a job you cannot see is harder to debug than a function
call you can.

## Running it

**Locally, you do not have to run anything.** With no `CELERY_BROKER_URL` set, jobs run
inline in the request, exactly as they did before Celery existed. `runserver` and
`pytest` need no broker, no worker, and no Redis.

To run it properly, which you should do at least once before deploying:

```bash
redis-server                                  # the broker

# in .env
CELERY_BROKER_URL=redis://localhost:6379/0

celery -A config worker --loglevel=info       # a second terminal
python manage.py runserver                    # a third
```

The worker prints the tasks it found at startup. If `authentication.tasks.send_email`
is not in that list, it will never run:

```
[tasks]
  . authentication.tasks.send_email
```

## In production

**The worker is a second process and you have to deploy it.** This is the mistake to
avoid: a web service alone, with `CELERY_BROKER_URL` set, queues every email into a
queue nobody is reading. Registration returns 201 and no code ever arrives, and
nothing in the web logs looks wrong.

On Railway, Render, Fly and similar, that means a second service from the same repo:

| Service | Command |
|---|---|
| web | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |
| worker | `celery -A config worker --loglevel=info --concurrency=4` |

Both need the same environment variables. See [deployment.md](deployment.md).

Staging and production **refuse to start** without a broker rather than silently
falling back to inline sending, because inline sending in production is a latency bug
that only shows up under load.

## Retries

A failed send is retried three times with exponential backoff and jitter
(`EMAIL_MAX_RETRIES`). Retries apply to things that might work on a second attempt,
an outage, a timeout, a rate limit.

They deliberately do **not** apply to a missing template id or an unknown provider.
Those are checked before the job is queued, because the answer cannot change between
now and when a worker picks it up, and a job that can only fail should never enter the
queue.

After the last retry the job is dropped and the failure is logged. The user is not
told, which is why every code-carrying email has a resend path.

## Writing a task

```python
@shared_task
def do_the_thing(user_id, amount):
    ...
```

Three rules, each of which has cost somebody a bad afternoon:

1. **Pass ids, not objects.** Arguments are serialized to JSON and may be read seconds
   later by another process. A model instance cannot cross that gap, and a stale copy
   of one is worse than an id, refetch inside the task.
2. **Assume it runs twice.** A queue delivers *at least* once. If running your task
   twice would charge someone twice, make it idempotent.
3. **Never log a code, a token or a password.** Worker logs are logs like any other.

## Testing

`CELERY_TASK_ALWAYS_EAGER` is on for the whole suite, so `.delay()` runs the task
immediately, in-process. Tests read as though the work were still synchronous, and no
test needs a broker.

`CELERY_TASK_EAGER_PROPAGATES` is deliberately **off**. With it on, an exception inside
a task would surface as an exception in the request that queued it, which is neither
what production does nor what you want in development, where a dead email provider
would start returning 500s from registration.

To prove work is actually handed over rather than done inline, patch the task:

```python
with patch("authentication.tasks.send_email.delay") as queued:
    api_client.post(reverse("register"), payload, format="json")

assert queued.call_count == 1
```

See `authentication/tests/tasks/test_send_email.py`.
