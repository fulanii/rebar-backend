from .delete_account import AccountDeletionView
from .email import EmailChangeConfirmView, EmailChangeRequestView
from .password import PasswordChangeView, PasswordResetConfirmView, PasswordResetRequestView
from .update import ProfileUpdateView

__all__ = [
    "ProfileUpdateView",
    "EmailChangeRequestView",
    "EmailChangeConfirmView",
    "PasswordResetRequestView",
    "PasswordResetConfirmView",
    "PasswordChangeView",
    "AccountDeletionView",
]
