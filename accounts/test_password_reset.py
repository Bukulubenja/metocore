import re

import pytest
from django.core import mail

from accounts.models import User


@pytest.fixture
def teacher():
    return User.objects.create_user(
        username="jdoe", password="the-old-password!", email="jdoe@example.com"
    )


@pytest.mark.django_db
def test_password_reset_page_renders(client):
    response = client.get("/accounts/password_reset/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_password_reset_sends_email_for_existing_user(client, teacher):
    response = client.post("/accounts/password_reset/", {"email": "jdoe@example.com"})

    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert "jdoe@example.com" in mail.outbox[0].to


@pytest.mark.django_db
def test_password_reset_does_not_reveal_whether_email_exists(client):
    response = client.post("/accounts/password_reset/", {"email": "nobody@example.com"})

    assert response.status_code == 302
    assert response.url == "/accounts/password_reset/done/"
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_full_password_reset_flow_changes_password(client, teacher):
    client.post("/accounts/password_reset/", {"email": "jdoe@example.com"})
    reset_link = re.search(r"/accounts/reset/\S+/", mail.outbox[0].body).group()

    confirm_response = client.get(reset_link, follow=True)
    assert confirm_response.status_code == 200

    submit_response = client.post(
        confirm_response.request["PATH_INFO"],
        {"new_password1": "a-brand-new-passw0rd!", "new_password2": "a-brand-new-passw0rd!"},
    )
    assert submit_response.status_code == 302
    assert submit_response.url == "/accounts/reset/done/"

    teacher.refresh_from_db()
    assert teacher.check_password("a-brand-new-passw0rd!") is True
    assert teacher.check_password("the-old-password!") is False
