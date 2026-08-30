# Recipe: send an email

All email goes through `authentication/utils/email/`. The package picks a provider
from `EMAIL_PROVIDER` and hands it a template id and some variables — there is no HTML
anywhere in the codebase.

```
authentication/utils/email/
├── __init__.py     the public senders + provider dispatch
├── brevo.py        send(to_email, template_id, variables) -> bool
└── resend.py       send(to_email, template_id, variables) -> bool
```

See [../../email-templates.md](../../email-templates.md) for building the templates
themselves.

---

## 1. Create and activate the template

Before writing any code. Note its id, and decide which variables it needs — the keys
are case-sensitive, and the convention here is capitals: `FIRST_NAME`, `CODE`.

Brevo ids are integers, Resend's are strings. **Activate (Brevo) or publish (Resend)
the template** — a draft cannot be sent.

---

## 2. Add the template id as a setting

In `config/settings/base.py`, beside the existing ones:

```python
WELCOME_TEMPLATE_ID = os.getenv("WELCOME_TEMPLATE_ID", "")
```

No provider prefix: the id belongs to whichever provider is configured. Add the
variable to all three `.env*.example` files.

---

## 3. Add a sender

In `authentication/utils/email/__init__.py`, beside the existing ones:

```python
def send_welcome_email(to_email, first_name):
    """
    Email a newly verified user.

    Template: `WELCOME_TEMPLATE_ID`
    Variables: `FIRST_NAME`
    """
    return _send(
        to_email,
        template_id=settings.WELCOME_TEMPLATE_ID,
        variables={"FIRST_NAME": first_name},
    )
```

Export it from `authentication/utils/__init__.py`, and document its variables in
[../../email-templates.md](../../email-templates.md).

`_send` handles the provider choice, the missing-id check and the logging. Your
function only decides which template and which variables.

Variable values must be strings or numbers. A code is a **string**: `"004821"` as a
number loses its leading zeros.

---

## 4. Call it from a view

```python
send_welcome_email(user.email, user.first_name)
```

No `try` needed. `_send` never raises: a provider outage is logged and the user's
request still succeeds. That is deliberate — a signup should not fail with a 500
because an email service had a bad minute.

Which means: **never rely on the return value for correctness.** If the email must
arrive, give the user a way to request it again.

---

## 5. Test it

`block_outbound_email` is autouse and patches **both** providers, so no test can send
a real email in any code path. Name the fixture to inspect what was sent:

```python
def test_welcome_uses_the_template(self, api_client, block_outbound_email, settings):
    settings.EMAIL_PROVIDER = "brevo"
    settings.WELCOME_TEMPLATE_ID = "7"
    ...
    kwargs = block_outbound_email.brevo_send.call_args.kwargs
    assert kwargs["template_id"] == 7
    assert kwargs["params"]["FIRST_NAME"] == "Jane"
```

`block_outbound_email.called` is true if either provider was used, so a test that only
cares that an email was attempted needs no provider setup. Use `.brevo_send` or
`.resend` when you need the actual arguments.

Test that the right variables are sent. Whether the template *renders* nicely is the
provider's side — check that by sending yourself one from their dashboard.

Never write a test that hits a provider for real. It is slow, flaky, costs quota, and
fails whenever their API is down.

---

## Adding a provider

One file and one dict entry — see the end of
[../../email-templates.md](../../email-templates.md).

---

## Local development

Three things can be missing, and they log differently:

```
[WARNING] event=email_not_sent reason=no_api_key provider=brevo to=jane@example.com
[ERROR]   event=email_not_sent reason=no_template_id to=jane@example.com
[ERROR]   event=email_not_sent reason=unknown_provider provider=mailgun known=brevo,resend
```

All are expected locally before you have set anything up. Any of them in production
means users are not receiving that email.

For registration you do not need email working at all — the account exists either way.
The code is hashed in the database and cannot be read back, so to test the full flow
either set a real API key, or temporarily log the raw code in the registration view
and remove that line before committing. Never log codes in a deployed environment.

---

## Moving email to a background queue

Sending inside the request adds its latency to the user's wait. At real volume, move
it to Celery: add the broker, wrap `_send` in a task, and call `.delay(...)`. Only
`utils/email/__init__.py` and the call sites change, which is the reason for the
indirection.
