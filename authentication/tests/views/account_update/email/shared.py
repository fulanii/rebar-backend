"""Shared by the email-change tests, mirroring the shared.py in the views package."""

from django.urls import reverse

NEW_EMAIL = "moved@example.com"


def request_change(client, user_password, new_email=NEW_EMAIL):
    return client.post(
        reverse("change-email"),
        {"new_email": new_email, "password": user_password},
        format="json",
    )
