"""Pagination classes, one per list endpoint. See docs/ai/conventions.md."""

from rest_framework.pagination import CursorPagination, PageNumberPagination


class UserPageNumberPagination(PageNumberPagination):
    """25 a page, capped at 100, with the total count. The order comes from the query."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class SuspensionCursorPagination(CursorPagination):
    """Newest suspension first, 25 at a time, capped at 100."""

    ordering = "-suspended_at"
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
