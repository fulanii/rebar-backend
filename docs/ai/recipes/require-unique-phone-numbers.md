# Recipe: require unique phone numbers

Out of the box, two accounts may share a phone number. That is the right default —
families and small businesses genuinely share one line, and blocking it turns away
real users.

If you are using the phone number as an anti-abuse signal (one trial per person, say),
you may want it unique instead. Three changes.

---

## 1. The model — `authentication/models/custom_user.py`

```python
phone_number = models.CharField(max_length=15, blank=True, default="", unique=True)
```

**This will not work as written**, and the reason matters: `unique=True` treats every
empty string as equal, so the *second* Google sign-up — which has no phone number —
collides with the first. Use a conditional constraint instead, which only applies to
rows that actually have a number:

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["phone_number"],
            condition=~models.Q(phone_number=""),
            name="unique_phone_number_when_present",
        )
    ]
```

---

## 2. The serializer — `authentication/serializers/user_registration.py`

The constraint gives a database error; the serializer gives a readable message.

```python
def validate_phone_number(self, value):
    digits = validate_us_phone_number(value)

    if CustomUser.objects.filter(phone_number=digits).exists():
        raise serializers.ValidationError("An account with this phone number already exists.")

    return digits
```

Note the order: normalize **first**, then check. Checking the raw input would let
`555-123-4567` and `(555) 123-4567` both through as different numbers.

---

## 3. Migrate

```bash
python manage.py makemigrations
python manage.py migrate
```

If you already have duplicate numbers in the database, the migration will fail. Find
them first:

```python
from django.db.models import Count
CustomUser.objects.exclude(phone_number="").values("phone_number").annotate(
    n=Count("id")).filter(n__gt=1)
```

---

## 4. Test it

```python
def test_duplicate_phone_number_is_rejected(self, api_client, base_user):
    response = api_client.post(
        reverse("register"), payload(phone_number=base_user.phone_number), format="json"
    )
    assert response.status_code == 400

def test_two_google_users_without_phone_numbers_can_coexist(self, api_client):
    """The empty-string case the plain unique=True would have broken."""
```

---

## One caveat

This leaks information. An attacker can now discover whether a given phone number has
an account by trying to register with it — the same problem the login endpoint
carefully avoids (see [../guardrails.md](../guardrails.md) §4). If that matters more
to you than the anti-abuse benefit, do the check silently: accept the registration and
flag the account for review instead of rejecting it.
