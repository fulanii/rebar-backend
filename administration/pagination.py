"""Pagination classes, one per list endpoint. See docs/ai/conventions.md."""

from rest_framework.pagination import CursorPagination


class UserCursorPagination(CursorPagination):
    """Newest signups first, 25 at a time, capped at 100."""

    ordering = "-date_joined"
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
