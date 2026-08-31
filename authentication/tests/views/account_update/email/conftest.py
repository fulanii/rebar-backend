"""Fixtures shared by the email-change tests."""

from unittest.mock import patch

import pytest

from authentication.models import EmailChange
from authentication.utils import issue_code

from .shared import NEW_EMAIL


@pytest.fixture
def pending_change(base_user):
    """A live email-change code for `base_user`, already aimed at NEW_EMAIL."""
    with patch("authentication.utils.generate_code.secrets.randbelow", return_value=123456):
        code = issue_code(EmailChange, base_user)

    EmailChange.objects.filter(user=base_user).update(new_email=NEW_EMAIL)
    return code
