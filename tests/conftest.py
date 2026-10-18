import dataclasses

import pytest

from app.services import email_service


@pytest.fixture(autouse=True)
def never_send_email(monkeypatch):
    """Tests read .env, which may hold real SMTP settings; never use them."""
    monkeypatch.setattr(email_service, "settings", dataclasses.replace(email_service.settings, smtp_host=""))
