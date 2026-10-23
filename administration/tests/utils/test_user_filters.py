"""
`filtered_users`, the one definition of which accounts match a set of admin filters.

The admin list and, later, email campaigns both read it, so what an operator previews
is what a campaign reaches. Every filter is tested sent and not sent: the failure that
matters is a filter applying when nobody asked for it.
"""

from datetime import datetime, timezone
from urllib.parse import urlencode

import pytest
from django.http import QueryDict
from rest_framework.exceptions import ValidationError

from administration.utils import filtered_users
from authentication.models import CustomUser

pytestmark = pytest.mark.django_db


def make(email, **fields):
    fields.setdefault("first_name", "Test")
    fields.setdefault("last_name", "Person")
    return CustomUser.objects.create(email=email, **fields)


def emails(query=""):
    return [user.email for user in filtered_users(QueryDict(query))]


class TestNoFilters:
    def test_every_account_comes_back(self):
        make("a@example.com", is_active=True)
        make("b@example.com", is_active=False, is_suspended=True)

        assert sorted(emails()) == ["a@example.com", "b@example.com"]

    def test_a_boolean_that_was_not_sent_filters_nothing(self):
        """
        DRF reads a missing boolean query param as `False`. Without `OptionalBooleanField`
        a search alone would also mean inactive, unverified, unsuspended non-staff.
        """
        make("staff@example.com", is_staff=True, is_active=True, is_verified=True, is_suspended=True)

        assert emails("search=staff") == ["staff@example.com"]

    def test_query_params_the_filter_does_not_own_are_ignored(self):
        """`page` and `page_size` belong to the paginator."""
        make("a@example.com")

        assert emails("page=1&page_size=5") == ["a@example.com"]


class TestExactFilters:
    @pytest.mark.parametrize("field", ["is_active", "is_verified", "is_suspended", "is_staff"])
    def test_a_flag_matches_both_ways(self, field):
        make("on@example.com", **{field: True})
        make("off@example.com", **{field: False})

        assert emails(f"{field}=true") == ["on@example.com"]
        assert emails(f"{field}=false") == ["off@example.com"]

    def test_auth_provider(self):
        make("google@example.com", auth_provider="google")
        make("email@example.com", auth_provider="email")

        assert emails("auth_provider=google") == ["google@example.com"]

    def test_filters_combine_with_and(self):
        make("both@example.com", is_active=True, auth_provider="google")
        make("one@example.com", is_active=True, auth_provider="email")

        assert emails("is_active=true&auth_provider=google") == ["both@example.com"]


class TestSearch:
    @pytest.fixture(autouse=True)
    def accounts(self):
        make("ines.dubois@example.com", first_name="Ines", last_name="Dubois")
        make("ines.kim@example.com", first_name="Ines", last_name="Kim")
        make("theo@example.com", first_name="Theo", last_name="Dubois")

    def test_a_fragment_matches_any_of_the_three_fields(self):
        assert sorted(emails("search=dubois")) == ["ines.dubois@example.com", "theo@example.com"]

    def test_it_ignores_case(self):
        assert len(emails("search=INES")) == 2

    def test_every_word_has_to_match(self):
        """So a full name finds one person rather than everyone sharing either half."""
        assert emails("search=ines dubois") == ["ines.dubois@example.com"]

    def test_a_blank_search_filters_nothing(self):
        assert len(emails("search=")) == 3


class TestPhone:
    @pytest.fixture(autouse=True)
    def accounts(self):
        make("paris@example.com", phone_number="+33612345678")
        make("newark@example.com", phone_number="+12015550123")
        make("none@example.com", phone_number="")

    @pytest.mark.parametrize("typed", ["612345678", "+33 6 12", "6-12-34"])
    def test_digits_match_anywhere_in_the_number(self, typed):
        assert emails(urlencode({"phone": typed})) == ["paris@example.com"]

    def test_a_phone_with_no_digits_is_refused(self):
        with pytest.raises(ValidationError) as error:
            emails("phone=abc")

        assert "phone" in error.value.detail

    def test_has_phone(self):
        assert sorted(emails("has_phone=true")) == ["newark@example.com", "paris@example.com"]
        assert emails("has_phone=false") == ["none@example.com"]


class TestHasLoggedIn:
    def test_it_splits_on_last_login(self):
        make("seen@example.com", last_login=datetime(2026, 10, 1, tzinfo=timezone.utc))
        make("never@example.com", last_login=None)

        assert emails("has_logged_in=true") == ["seen@example.com"]
        assert emails("has_logged_in=false") == ["never@example.com"]


class TestJoinedDates:
    @pytest.fixture(autouse=True)
    def accounts(self):
        late_evening = datetime(2026, 10, 1, 23, 30, tzinfo=timezone.utc)
        make("late@example.com", date_joined=late_evening)
        make("earlier@example.com", date_joined=datetime(2026, 9, 15, tzinfo=timezone.utc))

    def test_both_bounds_include_the_day_they_name(self):
        assert emails("joined_after=2026-10-01&joined_before=2026-10-01") == ["late@example.com"]

    def test_the_day_is_counted_in_the_callers_zone(self):
        """23:30 UTC on the 1st is already the 2nd in Niamey, an hour ahead."""
        assert emails("joined_after=2026-10-02") == []
        assert emails("joined_after=2026-10-02&timezone=Africa/Niamey") == ["late@example.com"]

    def test_bounds_the_wrong_way_round_are_refused(self):
        with pytest.raises(ValidationError) as error:
            emails("joined_after=2026-10-02&joined_before=2026-10-01")

        assert "joined_before" in error.value.detail

    @pytest.mark.parametrize("zone", ["Mars/Base", "../etc/passwd"])
    def test_an_unknown_time_zone_is_refused(self, zone):
        with pytest.raises(ValidationError):
            emails(urlencode({"timezone": zone}))

    def test_a_blank_time_zone_means_utc(self):
        assert emails("joined_after=2026-10-02&timezone=") == []


class TestOrdering:
    def test_the_default_is_newest_signup_first(self):
        make("old@example.com", date_joined=datetime(2026, 1, 1, tzinfo=timezone.utc))
        make("new@example.com", date_joined=datetime(2026, 10, 1, tzinfo=timezone.utc))

        assert emails() == ["new@example.com", "old@example.com"]

    @pytest.mark.parametrize("ordering", ["last_login", "-last_login"])
    def test_accounts_that_never_signed_in_sort_last_either_way(self, ordering):
        make("never@example.com", last_login=None)
        make("seen@example.com", last_login=datetime(2026, 10, 1, tzinfo=timezone.utc))

        assert emails(f"ordering={ordering}")[-1] == "never@example.com"

    def test_ties_fall_back_to_id(self):
        """Without it, rows sharing a value can come back in any order, per page."""
        first, second = make("a@example.com"), make("b@example.com")

        assert [u.pk for u in filtered_users(QueryDict("ordering=first_name"))] == [first.pk, second.pk]
        assert [u.pk for u in filtered_users(QueryDict("ordering=-first_name"))] == [second.pk, first.pk]

    def test_a_field_off_the_list_is_refused(self):
        """Nothing a caller sends reaches `order_by` unless it is on the allowlist."""
        with pytest.raises(ValidationError) as error:
            emails("ordering=password")

        assert "ordering" in error.value.detail
