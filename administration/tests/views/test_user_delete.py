"""
Deleting an account for good.

The only irreversible endpoint in the API, so the tests are mostly about what goes
with the row: the suspension history hanging off it, the tokens that keep it signed
in, and the records it wrote about other people, which have to survive it.
"""

import pytest
from django.urls import reverse
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from administration.models import Suspension
from authentication.models import CustomUser

pytestmark = pytest.mark.django_db


def url(user):
    return reverse("admin-user-delete", args=[user.pk])


class TestAccess:
    def test_an_anonymous_request_is_refused(self, api_client, base_user):
        assert api_client.delete(url(base_user)).status_code == 401

    def test_a_signed_in_user_is_refused(self, auth_client, second_user):
        assert auth_client.delete(url(second_user)).status_code == 403

    def test_staff_alone_is_not_enough(self, admin_client, base_user):
        """Nothing recoverable is at stake elsewhere in this app. Here everything is."""
        response = admin_client.delete(url(base_user))

        assert response.status_code == 403
        assert CustomUser.objects.filter(pk=base_user.pk).exists()

    def test_a_superuser_is_allowed_through(self, superuser_client, base_user):
        assert superuser_client.delete(url(base_user)).status_code == 200

    def test_a_suspended_superuser_is_refused(self, superuser, base_user, token_client):
        superuser.is_suspended = True
        superuser.save(update_fields=["is_suspended"])

        response = token_client(superuser).delete(url(base_user))

        assert response.status_code == 401
        assert CustomUser.objects.filter(pk=base_user.pk).exists()


class TestDeleting:
    def test_the_account_is_gone(self, superuser_client, base_user):
        superuser_client.delete(url(base_user))

        assert not CustomUser.objects.filter(pk=base_user.pk).exists()

    def test_the_receipt_says_what_went(self, superuser_client, superuser, base_user):
        """The account cannot be looked up afterwards, so the response is the only record."""
        Suspension.objects.create(user=base_user, reason="fraud", suspended_by=superuser)
        Suspension.objects.create(user=base_user, reason="spam", suspended_by=superuser)

        response = superuser_client.delete(url(base_user))

        assert response.data == {
            "id": base_user.pk,
            "email": base_user.email,
            "suspensions_deleted": 2,
        }

    def test_an_account_with_no_history_reports_none(self, superuser_client, base_user):
        assert superuser_client.delete(url(base_user)).data["suspensions_deleted"] == 0

    def test_it_takes_the_suspension_history_with_it(self, superuser_client, superuser, base_user):
        """
        The cascade, stated so it is a decision rather than a surprise.

        An account deleted after a fraud investigation takes the record of that
        investigation with it. `docs/ai/recipes/soft-delete-accounts.md` is the
        alternative when that is not acceptable.
        """
        Suspension.objects.create(user=base_user, reason="fraud", suspended_by=superuser)

        superuser_client.delete(url(base_user))

        assert Suspension.objects.count() == 0

    def test_it_signs_the_account_out_everywhere(self, superuser_client, base_user):
        """Outstanding refresh tokens cascade, so no session outlives the account."""
        RefreshToken.for_user(base_user)
        assert OutstandingToken.objects.filter(user=base_user).exists()

        superuser_client.delete(url(base_user))

        assert not OutstandingToken.objects.filter(user_id=base_user.pk).exists()

    def test_records_the_account_issued_survive_it(self, superuser_client, base_user, user_password):
        """
        What somebody did outlives their account: `suspended_by` is SET_NULL, not CASCADE.

        Deleting an operator must not erase the suspensions they handed out, or firing
        one would quietly rewrite why every account they touched was locked.
        """
        operator = CustomUser.objects.create_superuser(
            email="operator@example.com", password=user_password, first_name="Ops", last_name="Two"
        )
        Suspension.objects.create(user=base_user, reason="abuse", suspended_by=operator)

        superuser_client.delete(url(operator))

        record = Suspension.objects.get(user=base_user)
        assert record.reason == "abuse"
        assert record.suspended_by is None


class TestRefusals:
    def test_nobody_deletes_themselves(self, superuser_client, superuser):
        """A superuser deleting its own row leaves nobody able to undo it."""
        response = superuser_client.delete(url(superuser))

        assert response.status_code == 400
        assert "your own account" in str(response.data).lower()
        assert CustomUser.objects.filter(pk=superuser.pk).exists()

    def test_an_unknown_id_is_a_404(self, superuser_client, base_user):
        target = reverse("admin-user-delete", args=[base_user.pk + 999])

        assert superuser_client.delete(target).status_code == 404

    def test_deleting_the_same_account_twice_is_a_404(self, superuser_client, base_user):
        """The second call must not read as success: nothing was deleted by it."""
        target = url(base_user)
        assert superuser_client.delete(target).status_code == 200

        assert superuser_client.delete(target).status_code == 404
