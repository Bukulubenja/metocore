import datetime

import pytest
from django.utils import timezone

from accounts.models import SchoolAdminInvitation, User
from schools.models import School


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.fixture
def platform_admin():
    return User.objects.create_superuser(username="platform", password="x", email="p@example.com")


@pytest.fixture
def invitation(school, platform_admin):
    return SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )


@pytest.mark.django_db
def test_accept_page_renders_for_valid_token(client, invitation):
    response = client.get(f"/invitations/{invitation.token}/accept/")

    assert response.status_code == 200
    assert b"new.admin@example.com" in response.content


@pytest.mark.django_db
def test_accept_page_returns_404_for_unknown_token(client):
    response = client.get("/invitations/does-not-exist/accept/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_accept_page_returns_410_for_expired_invitation(client, invitation):
    invitation.expires_at = timezone.now() - datetime.timedelta(days=1)
    invitation.save(update_fields=["expires_at"])

    response = client.get(f"/invitations/{invitation.token}/accept/")

    assert response.status_code == 410


@pytest.mark.django_db
def test_accepting_creates_account_and_logs_in(client, invitation, school):
    response = client.post(
        f"/invitations/{invitation.token}/accept/",
        {"username": "newadmin", "password": "a-quite-unguessable-pw"},
    )

    assert response.status_code == 302
    assert response.url == "/home/"
    user = User.objects.get(username="newadmin")
    assert user.role == User.Role.ADMIN
    assert user.school == school

    home_response = client.get("/home/")
    assert home_response.status_code == 302
    assert home_response.url == "/dashboard/"

    dashboard_response = client.get("/dashboard/")
    assert dashboard_response.status_code == 200


@pytest.mark.django_db
def test_accepting_with_taken_username_shows_error(client, invitation, school):
    User.objects.create_user(username="newadmin", password="x", school=school)

    response = client.post(
        f"/invitations/{invitation.token}/accept/",
        {"username": "newadmin", "password": "a-quite-unguessable-pw"},
    )

    assert response.status_code == 200
    assert b"already taken" in response.content
    invitation.refresh_from_db()
    assert invitation.accepted_at is None


@pytest.mark.django_db
def test_accepting_with_weak_password_shows_error(client, invitation):
    response = client.post(
        f"/invitations/{invitation.token}/accept/",
        {"username": "newadmin", "password": "123"},
    )

    assert response.status_code == 200
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not User.objects.filter(username="newadmin").exists()


@pytest.mark.django_db
def test_accepting_teacher_invitation_redirects_to_check_in_page(client, school, platform_admin):
    teacher_invitation = SchoolAdminInvitation.create_for(
        email="new.teacher@example.com",
        school=school,
        invited_by=platform_admin,
        role=User.Role.TEACHER,
    )

    response = client.post(
        f"/invitations/{teacher_invitation.token}/accept/",
        {"username": "newteacher", "password": "a-quite-unguessable-pw"},
    )

    assert response.status_code == 302
    assert response.url == "/home/"

    home_response = client.get("/home/")
    assert home_response.url == "/check-in/"


@pytest.mark.django_db
def test_accepting_already_accepted_invitation_returns_410(client, invitation):
    invitation.accept(username="firstadmin", password="a-quite-unguessable-pw")

    response = client.post(
        f"/invitations/{invitation.token}/accept/",
        {"username": "secondadmin", "password": "another-unguessable-pw"},
    )

    assert response.status_code == 410
