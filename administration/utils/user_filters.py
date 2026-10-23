"""Which accounts match a set of admin filters. The one definition of it, see docs/endpoints.md."""

from django.db.models import F, Q
from django.db.models.functions import TruncDate

from administration.serializers import UserListQueryRequestSerializer
from authentication.models import CustomUser

EXACT_FILTERS = ("is_active", "is_verified", "is_phone_verified", "is_suspended", "is_staff", "auth_provider")

SEARCH_FIELDS = ("email", "first_name", "last_name")

JOINED_BOUNDS = {"joined_after": "joined_on__gte", "joined_before": "joined_on__lte"}


def filtered_users(query_params):
    """
    Every account matching `query_params`, in the order they asked for.

    Invalid params raise `ValidationError`, so a typo is a 400 naming the field rather
    than the whole table returned as if it were the filtered result.
    """
    query = UserListQueryRequestSerializer(data=query_params)
    query.is_valid(raise_exception=True)
    filters = query.validated_data

    users = CustomUser.objects.filter(**{field: filters[field] for field in EXACT_FILTERS if field in filters})

    for term in filters.get("search", "").split():
        users = users.filter(Q(**{f"{field}__icontains": term for field in SEARCH_FIELDS}, _connector=Q.OR))

    if filters.get("phone"):
        users = users.filter(phone_number__contains=filters["phone"])

    if "has_phone" in filters:
        users = users.exclude(phone_number="") if filters["has_phone"] else users.filter(phone_number="")

    if "has_logged_in" in filters:
        users = users.filter(last_login__isnull=not filters["has_logged_in"])

    bounds = {lookup: filters[param] for param, lookup in JOINED_BOUNDS.items() if param in filters}

    if bounds:
        users = users.annotate(joined_on=TruncDate("date_joined", tzinfo=filters["timezone"])).filter(**bounds)

    return users.order_by(*ordering(filters["ordering"]))


def ordering(requested):
    """The sort asked for, empty values last either way, then `id` so ties never reshuffle."""
    field = requested.lstrip("-")

    if requested.startswith("-"):
        return F(field).desc(nulls_last=True), "-id"

    return F(field).asc(nulls_last=True), "id"
