# Recipe: add a model

Worked example: an `ApiKey` a user can generate.

---

## 1. Write the model — `<app>/models/api_key.py`

One file per model.

```python
from django.conf import settings
from django.db import models


class ApiKey(models.Model):
    """
    A long-lived key a user can use instead of signing in.

    The key is stored hashed, exactly like a password: a leaked database must not
    hand over working keys. `prefix` is the first few visible characters, so the UI
    can show "which key is this" without being able to reproduce it.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,        # never import the user model directly
        on_delete=models.CASCADE,        # delete the user, delete their keys
        related_name="api_keys",         # user.api_keys.all()
    )
    # Not null=True: absent is "", per the project convention.
    label = models.CharField(max_length=100, blank=True, default="")
    prefix = models.CharField(max_length=8, db_index=True)
    hashed_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label or self.prefix} ({self.user.email})"
```

Points worth knowing:

- **`on_delete` is required** and it is a real decision. `CASCADE` deletes the rows
  with their owner; `PROTECT` refuses to delete a user who still has any; `SET_NULL`
  keeps them and empties the link.
- **`related_name`** is how you get from a user to their keys.
- **`null=True` is fine on dates and numbers**, where "unset" is genuinely different
  from zero. It is not fine on text fields — see [../conventions.md](../conventions.md).
- **`db_index=True`** on columns you will filter by. Not on everything: each index
  costs write speed and disk.
- **Rules that must always hold belong in the database**, via `unique=True` or a
  constraint in `Meta`. A serializer check can be bypassed; a constraint cannot.

---

## 2. Export it — `<app>/models/__init__.py`

```python
from .api_key import ApiKey

__all__ = [..., "ApiKey"]
```

---

## 3. Generate and apply the migration

```bash
python manage.py makemigrations
python manage.py migrate
```

Read what `makemigrations` prints. If it asks you to choose a default for a new
non-nullable column on an existing table, stop and think — the answer applies to
every row already there.

Commit the migration file. It is code.

**Never edit a migration that has already run.** Change the model and make a new one.

---

## 4. Register it in the admin (optional) — `<app>/admin.py`

```python
@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ["prefix", "user", "created_at", "revoked_at"]
    search_fields = ["user__email", "label"]
    readonly_fields = ["hashed_key"]
```

The admin is mounted under the dev settings only.

---

## 5. Test the model itself

Test the rules the model guarantees, separately from any endpoint:

```python
@pytest.mark.django_db
class TestApiKey:
    def test_deleting_the_user_deletes_their_keys(self, base_user):
        ...

    def test_the_raw_key_is_never_stored(self, base_user):
        ...
```

---

## 6. Then the API

The model is only storage. To expose it, follow
[add-an-endpoint.md](add-an-endpoint.md).
