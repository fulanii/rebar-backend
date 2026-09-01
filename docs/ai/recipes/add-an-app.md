# Recipe: add an app

An "app" is one self-contained feature area, `billing`, `projects`, `notifications`.
Keep `authentication` for accounts and put your product in new apps beside it.

---

## 1. Create it

```bash
python manage.py startapp billing
```

Then reshape it to match the house layout, replacing the single-file modules Django
generates with packages:

```bash
rm billing/models.py billing/views.py billing/tests.py
mkdir -p billing/{models,serializers,views,utils,tests/{models,views}}
touch billing/{models,serializers,views,utils}/__init__.py
touch billing/tests/__init__.py billing/tests/{models,views}/__init__.py
touch billing/urls.py billing/throttles.py
```

---

## 2. Register it, `config/settings/base.py`

```python
INSTALLED_APPS = [
    ...
    "authentication",
    "billing",       # ← add here, under "Local"
]
```

Django will not see the app, or its models, or its migrations, until it is listed.

---

## 3. Mount its URLs, `config/urls.py`

```python
path("billing/", include("billing.urls")),
```

---

## 4. Respect the dependency direction

Your app may import from `authentication` **only** through the public seams:

```python
from django.contrib.auth import get_user_model   # yes
from django.conf import settings                 # settings.AUTH_USER_MODEL, yes

from authentication.models import CustomUser     # no
```

Referring to the user model as `settings.AUTH_USER_MODEL` in a `ForeignKey` is not
stylistic: importing the class directly creates a circular import as soon as
`authentication` ever needs anything from your app.

`authentication` must never import from your app. Dependencies point one way.

---

## 5. Give it its own throttle scopes

Add rates to `DEFAULT_THROTTLE_RATES` in `config/settings/base.py` and classes in
`billing/throttles.py`. Namespace the scope names (`billing_checkout`, not
`checkout`) so two apps cannot collide.

---

## 6. Test it

Mirror the structure in `billing/tests/`. The fixtures in the root `conftest.py`
(`api_client`, `auth_client`, `base_user`, …) are available to every app
automatically, you do not need to redefine them.

App-specific fixtures go in `billing/tests/conftest.py`.

**Add the app to `testpaths` in `pyproject.toml`**, or its tests are collected by
nothing and silently never run:

```toml
testpaths = ["authentication", "billing", "config"]
```

Every app owns its own tests. There is no project-wide test folder, `config/tests/`
exists only for the schema guards, which check routing and the docs configuration
rather than any single app.

---

## 7. Add its docs

If the app has non-obvious rules (anything involving money, permissions, or state
machines especially) write them down in `docs/`. The next person to touch it will
be an assistant reading exactly what you left behind.
