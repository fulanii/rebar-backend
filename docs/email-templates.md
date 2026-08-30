# Email templates

The wording and design of every email live in a **template in your email provider's
dashboard**, not in the code. The backend sends a template id and a few variables;
the provider renders the rest.

```
backend   ->  template id + {"FIRST_NAME": "Jane", "CODE": "004821", ...}
provider  ->  renders and sends
```

Changing "Welcome, Jane" to "Hi Jane" is an edit in a dashboard, not a code change, a
pull request and a deploy. Non-technical people can own the copy.

## Choosing a provider

Two are supported. Pick one with `EMAIL_PROVIDER` in `.env`:

```
EMAIL_PROVIDER=brevo      # or resend
```

| | Brevo | Resend |
|---|---|---|
| Free tier | 300 emails/day, unlimited sending domains | 100 emails/day, **one** domain |
| Template id | an **integer**, e.g. `3` | a **string**, e.g. `tmpl_abc123` |
| Variable syntax in the template | `{{ params.FIRST_NAME }}` | the editor's variable control |
| Package | `brevo-python` | `resend` |

**Brevo is the default**, because the unlimited-domains free tier is the one that
survives contact with a second project. Resend's editor is nicer; if you are only
ever shipping one product, either is fine.

Switching provider is one line in `.env` plus rebuilding the two templates. Nothing
in the code changes — the variable names are identical on both sides.

You only need the package for the provider you use. Remove the other from
`requirements.txt` if you like.

## The two templates

| Template | Env variable | Sent when |
|---|---|---|
| Email verification | `VERIFICATION_TEMPLATE_ID` | Someone registers, or asks to resend the code |
| Password reset | `PASSWORD_RESET_TEMPLATE_ID` | Someone requests a password reset |

Both receive the same three variables, whichever provider you use:

| Key | Type | Example | Notes |
|---|---|---|---|
| `FIRST_NAME` | string | `Jane` | Never empty — registration requires a name. |
| `CODE` | string | `004821` | **A string, not a number.** Codes can start with zero. |
| `EXPIRY_MINUTES` | number | `15` | Read from the code model, so the email cannot promise a window the code does not honour. |

## Building them — Brevo

1. **Transactional → Templates → New template.**
2. Set the sender and the subject on the template itself; the backend does not send
   either.
3. In the body, insert variables as `{{ params.FIRST_NAME }}`, `{{ params.CODE }}`,
   `{{ params.EXPIRY_MINUTES }}`. The `params.` prefix is required — a bare
   `{{ CODE }}` renders empty.
4. **Save and activate it.** An inactive template will not send.
5. The template id is the number in the list (`3`, `4`, …). Put it in `.env`.

## Building them — Resend

1. Create a template and note its id.
2. Add the three variables, matching the keys exactly — they are case-sensitive.
3. Insert them with the editor's variable control rather than typing placeholder
   syntax by hand.
4. **Publish it.** A template left in `draft` cannot be sent.
5. Put the id in `.env`.

## What each email should say

Not rules, but these three earn their place:

- **The code itself, large and easy to copy.** It is the only reason the email exists.
- **How long it lasts** — use `EXPIRY_MINUTES` rather than writing "15" into the copy,
  or the two drift the first time someone changes the model.
- **"If you did not request this, ignore this email."** Password-reset emails reach
  people who did not ask for them; that line is what stops them worrying.

Keep the HTML simple. Email clients strip `<style>` blocks and understand roughly
2003-era HTML — inline styles, simple layouts, no flexbox or grid.

Never put anything in these emails you would not want in a screenshot: they are
forwarded, quoted, and sit in inboxes for years.

## When something is missing

Nothing is sent, and the reason is logged. There is no fallback body — one path means
what users receive is always what you see in the dashboard, with no second, untested
version of each email hiding in the code.

```
[WARNING] event=email_not_sent reason=no_api_key provider=brevo to=jane@example.com
[ERROR]   event=email_not_sent reason=no_template_id to=jane@example.com
[ERROR]   event=email_not_sent reason=template_id_not_an_integer provider=brevo value='tmpl_x'
[ERROR]   event=email_not_sent reason=unknown_provider provider=mailgun known=brevo,resend
```

The third is the one to watch when switching provider: a Resend id left in `.env`
after moving to Brevo is refused rather than sent as garbage.

The practical consequence is that **both templates must exist before anyone can
register**, because verification is part of signing up. Do it before your first real
user. The account is still created when the email fails — only the code does not
arrive, and the user can request another one once the configuration is fixed.

## Testing

Emails never leave the test suite. The `block_outbound_email` fixture in `conftest.py`
patches **both** providers' network calls for every test automatically, so no test can
send mail or depend on either service being up.

```python
def test_verification_uses_the_template(self, api_client, block_outbound_email, settings):
    settings.EMAIL_PROVIDER = "brevo"
    ...
    kwargs = block_outbound_email.brevo_send.call_args.kwargs
    assert kwargs["template_id"] == 3
    assert kwargs["params"]["CODE"]
```

`block_outbound_email.called` is true if **either** provider was used, so tests that
only care that an email was attempted work whichever provider is configured. Use
`.resend` and `.brevo_send` when you need the actual arguments.

To check a template really renders, send yourself one from the provider's dashboard.
That tests the template; the tests here cover the code that calls it.

## Adding another email

1. Create and activate the template.
2. Add a `<NAME>_TEMPLATE_ID` setting in `config/settings/base.py` and to all three
   `.env*.example` files.
3. Add a sender function in `authentication/utils/email/__init__.py` following
   `send_verification_email`, and export it from `authentication/utils/__init__.py`.
4. Document its variables in the table above.

Step-by-step: [ai/recipes/send-an-email.md](ai/recipes/send-an-email.md).

## Adding another provider

One file and one dict entry:

1. Write `authentication/utils/email/<name>.py` with a single
   `send(to_email, template_id, variables) -> bool`. Import its SDK **inside** the
   function so the package is only needed when that provider is selected.
2. Add it to `PROVIDERS` in `authentication/utils/email/__init__.py`.
3. Patch its network call in `conftest.py`'s `block_outbound_email`, or the suite can
   send real email through it.

Nothing outside that package changes.
