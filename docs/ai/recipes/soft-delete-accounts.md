# Keep records when an account is deleted

`POST auth/delete-account/` hard-deletes the user row. That is the right default: it
is what a person asking to be deleted means, and it is what data-protection law
expects you to actually do.

Some products cannot. If you have invoices, audit trails, or rows that must survive
for tax or compliance reasons, replace the delete with an anonymisation.

## The change

`authentication/views/account_deletion.py`, in place of `user.delete()`:

```python
user.email = f"deleted-{user.pk}@example.invalid"
user.first_name = "Deleted"
user.last_name = "User"
user.phone_number = ""
user.is_active = False
user.is_verified = False
user.set_unusable_password()
user.save()
```

`example.invalid` is reserved by RFC 2606 and can never be delivered to, so the row
keeps a unique address without ever reaching a real person.

Revoking sessions first still applies, and matters more here: the row survives, so a
live token must not.

## What this costs you

- **The address is not released.** The person cannot sign up again with it, because a
  row still holds it. Free it by moving the address to a nullable column before
  overwriting, or accept the limitation and say so in your product.
- **It is not deletion.** If you are subject to GDPR or CCPA, an anonymised row is
  only defensible when nothing in it identifies the person any more. Check what your
  other tables still hold — an invoice with their name on it is still their data.
- **Your queries change.** Everything counting users now counts tombstones. Filter on
  `is_active` or add an explicit `is_deleted` flag.

Update the endpoint's docstring when you change this. It currently promises a hard
delete, and that docstring is your API documentation.
