import pytest

from accounts.models import User
from announcements.models import Announcement
from schools.models import School


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.fixture
def other_school():
    return School.objects.create(name="Hillcrest Academy")


@pytest.fixture
def school_admin(school):
    return User.objects.create_user(
        username="principal", password="x", role=User.Role.ADMIN, school=school
    )


@pytest.fixture
def teacher(school):
    return User.objects.create_user(
        username="jdoe", password="x", role=User.Role.TEACHER, school=school
    )


@pytest.fixture
def announcement(school, school_admin):
    return Announcement.objects.create(
        school=school, title="Sports day", body="Bring kit.", created_by=school_admin
    )


@pytest.mark.django_db
def test_announcement_list_requires_login(client):
    response = client.get("/announcements/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_teacher_can_view_announcements(client, teacher, announcement):
    client.force_login(teacher)

    response = client.get("/announcements/")

    assert response.status_code == 200
    assert b"Sports day" in response.content


@pytest.mark.django_db
def test_teacher_cannot_create_announcement(client, teacher, school):
    client.force_login(teacher)

    response = client.post(
        "/announcements/", {"title": "Fake", "body": "Nope."}
    )

    assert response.status_code == 403
    assert Announcement.objects.filter(title="Fake").exists() is False


@pytest.mark.django_db
def test_admin_can_create_announcement(client, school_admin, school):
    client.force_login(school_admin)

    response = client.post(
        "/announcements/", {"title": "Sports day", "body": "Bring kit."}
    )

    assert response.status_code == 302
    created = Announcement.objects.get(title="Sports day")
    assert created.school == school
    assert created.created_by == school_admin


@pytest.mark.django_db
def test_admin_can_delete_announcement(client, school_admin, announcement):
    client.force_login(school_admin)

    response = client.post(f"/announcements/{announcement.id}/delete/")

    assert response.status_code == 302
    assert Announcement.objects.filter(id=announcement.id).exists() is False


@pytest.mark.django_db
def test_teacher_cannot_delete_announcement(client, teacher, announcement):
    client.force_login(teacher)

    response = client.post(f"/announcements/{announcement.id}/delete/")

    assert response.status_code == 403
    assert Announcement.objects.filter(id=announcement.id).exists() is True


@pytest.mark.django_db
def test_announcements_scoped_to_own_school(client, school_admin, other_school):
    Announcement.objects.create(
        school=other_school, title="Other school event", body="x"
    )
    client.force_login(school_admin)

    response = client.get("/announcements/")

    assert response.status_code == 200
    assert b"Other school event" not in response.content
