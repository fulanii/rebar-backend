"""
Suspending and reinstating an account.

The flag is what `SuspensionAwareJWTAuthentication` reads on every request, so setting
it locks somebody out of a live session immediately. The row beside it is what answers
"why is this person locked out" six months later, and it is the half a plain flag
loses, so most of these tests are about the two staying in step.
"""

import pytest
from django.urls import reverse

from administration.models import Suspension

pytestmark = pytest.mark.django_db


def url(user):
    return reverse("admin-user-suspension", args=[user.pk])


def suspend(client, user, **body):
    return client.post(url(user), body or {"reason": "fraud"}, format="json")


class TestAccess:
    def test_an_anonymous_request_is_refused(self, api_client, base_user):
        assert suspend(api_client, base_user).status_code == 401

    def test_a_signed_in_user_is_refused(self, auth_client, second_user):
        assert suspend(auth_client, second_user).status_code == 403

    def test_staff_alone_is_not_enough(self, admin_client, base_user):
        """Locking a customer out is not a support action, it is a superuser one."""
        response = suspend(admin_client, base_user)

        base_user.refresh_from_db()
        assert response.status_code == 403
        assert base_user.is_suspended is False

    def test_a_superuser_is_allowed_through(self, superuser_client, base_user):
        assert suspend(superuser_client, base_user).status_code == 201

    def test_lifting_needs_a_superuser_too(self, admin_client, superuser_client, base_user):
        suspend(superuser_client, base_user)

        assert admin_client.delete(url(base_user)).status_code == 403

    def test_an_unknown_id_is_a_404(self, superuser_client, base_user):
        target = reverse("admin-user-suspension", args=[base_user.pk + 999])

        assert superuser_client.post(target, {"reason": "spam"}, format="json").status_code == 404


class TestSuspending:
    def test_it_sets_the_flag_and_writes_the_record(self, superuser_client, superuser, base_user):
        response = suspend(superuser_client, base_user, reason="fraud", notes="ticket SUP-1183")

        base_user.refresh_from_db()
        record = Suspension.objects.get(user=base_user)

        assert response.status_code == 201
        assert base_user.is_suspended is True
        assert (record.reason, record.notes, record.suspended_by) == ("fraud", "ticket SUP-1183", superuser)
        assert record.lifted_at is None

    def test_the_response_names_who_did_it(self, superuser_client, superuser, base_user):
        response = suspend(superuser_client, base_user)

        assert response.data["suspended_by"] == superuser.email
        assert response.data["lifted_by"] is None

    def test_the_reason_defaults_to_manual(self, superuser_client, base_user):
        response = superuser_client.post(url(base_user), {"notes": "no reason given"}, format="json")

        assert response.status_code == 201
        assert response.data["reason"] == "manual"

    def test_a_reason_outside_the_list_is_refused(self, superuser_client, base_user):
        response = superuser_client.post(url(base_user), {"reason": "vibes"}, format="json")

        base_user.refresh_from_db()
        assert response.status_code == 400
        assert base_user.is_suspended is False

    def test_a_live_session_stops_working_immediately(self, superuser_client, base_user, token_client):
        """
        The point of the flag: a token minted a second ago is refused on the next call.

        Suspension that waited for a token to expire would leave whoever is being
        locked out up to a full token lifetime of unimpeded use.
        """
        victim = token_client(base_user)
        assert victim.get(reverse("me")).status_code == 200

        suspend(superuser_client, base_user)

        response = victim.get(reverse("me"))

        assert response.status_code == 401
        assert response.data["code"] == "account_suspended"


class TestSuspendingRefuses:
    def test_nobody_suspends_themselves(self, superuser_client, superuser):
        """A superuser locking itself out cannot lift it, and neither can anybody below it."""
        response = suspend(superuser_client, superuser)

        superuser.refresh_from_db()
        assert response.status_code == 400
        assert "your own account" in str(response.data).lower()
        assert superuser.is_suspended is False

    def test_an_account_cannot_be_suspended_twice_over(self, superuser_client, base_user):
        """A second open record would leave the lift ambiguous about which one it closed."""
        suspend(superuser_client, base_user)

        response = suspend(superuser_client, base_user)

        assert response.status_code == 400
        assert "already suspended" in str(response.data).lower()
        assert Suspension.objects.filter(user=base_user).count() == 1


class TestLifting:
    def test_it_clears_the_flag_and_closes_the_record(self, superuser_client, superuser, base_user):
        suspend(superuser_client, base_user)

        response = superuser_client.delete(url(base_user))

        base_user.refresh_from_db()
        record = Suspension.objects.get(user=base_user)

        assert response.status_code == 200
        assert base_user.is_suspended is False
        assert record.lifted_at is not None
        assert record.lifted_by == superuser

    def test_the_record_survives_the_lift(self, superuser_client, base_user):
        """Deleting the row instead would erase the only answer to "why were they locked out"."""
        suspend(superuser_client, base_user, reason="chargeback")
        superuser_client.delete(url(base_user))

        assert Suspension.objects.filter(user=base_user, reason="chargeback").exists()

    def test_an_account_that_is_not_suspended_cannot_be_lifted(self, superuser_client, base_user):
        response = superuser_client.delete(url(base_user))

        assert response.status_code == 400
        assert "not suspended" in str(response.data).lower()

    def test_the_account_can_sign_in_again(self, superuser_client, base_user, user_password, api_client):
        suspend(superuser_client, base_user)
        superuser_client.delete(url(base_user))

        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": user_password}, format="json"
        )

        assert response.status_code == 200


class TestHistory:
    def test_every_suspension_leaves_its_own_row(self, superuser_client, base_user):
        """Three strikes is a question the history answers and a single flag cannot."""
        for reason in ("spam", "abuse", "fraud"):
            suspend(superuser_client, base_user, reason=reason)
            superuser_client.delete(url(base_user))

        records = Suspension.objects.filter(user=base_user)

        assert records.count() == 3
        assert [record.reason for record in records.order_by("suspended_at")] == ["spam", "abuse", "fraud"]
        assert all(record.lifted_at is not None for record in records)
