"""View exports. Import from the package, not from the module files."""

from .suspension import SuspensionListView, SuspensionView
from .user_details import UserDetailView
from .user_list import UserListView
from .user_update import UserUpdateView

__all__ = [
    "SuspensionListView",
    "SuspensionView",
    "UserDetailView",
    "UserListView",
    "UserUpdateView",
]
