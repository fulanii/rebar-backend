"""Fixtures shared by the password-flow tests."""

from unittest.mock import patch

import pytest

from authentication.models import PasswordReset
from authentication.utils import issue_code


@pytest.fixture
def reset_code(base_user):
    """A live reset code for `base_user`. Returns the raw digits."""
    with patch("authentication.utils.generate_code.secrets.randbelow", return_value=123456):
        return issue_code(PasswordReset, base_user)
