"""View exports. Import from the package, not from the module files."""

from .user_details import UserDetailView
from .user_list import UserListView

__all__ = [
    "UserDetailView",
    "UserListView",
]
