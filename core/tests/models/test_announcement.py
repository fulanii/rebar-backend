"""
The banner is one row, enforced by the database rather than only by `save()`.

`save()` is the path every endpoint takes, but a queryset `update()`, a `bulk_create`
or a shell session skips it. The constraints are what still hold then.
"""

import pytest
from django.db import IntegrityError, transaction

from core.models import Announcement

pytestmark = pytest.mark.django_db


class TestSingleton:
    def test_saving_twice_keeps_one_row(self):
        Announcement(message="First").save()
        Announcement(message="Second").save()

        assert Announcement.objects.count() == 1
        assert Announcement.current().message == "Second"

    def test_save_ignores_an_id_it_was_given(self):
        announcement = Announcement(pk=7, message="Hello")
        announcement.save()

        assert announcement.pk == Announcement.SINGLETON_ID

    def test_the_database_refuses_a_second_row(self):
        """A bulk insert skips `save()`, so this is the constraint working alone."""
        with pytest.raises(IntegrityError), transaction.atomic():
            Announcement.objects.bulk_create([Announcement(pk=2, message="Sneaky")])

    def test_current_is_none_before_anything_is_written(self):
        assert Announcement.current() is None


class TestAnActiveBannerHasAMessage:
    def test_the_database_refuses_an_active_empty_banner(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            Announcement(message="", is_active=True).save()

    def test_a_hidden_banner_may_be_empty(self):
        Announcement(message="", is_active=False).save()

        assert Announcement.current().message == ""
