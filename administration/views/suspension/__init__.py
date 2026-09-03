"""View exports. Import from the package, not from the module files."""

from .list import SuspensionListView
from .record import SuspensionView

__all__ = [
    "SuspensionListView",
    "SuspensionView",
]
