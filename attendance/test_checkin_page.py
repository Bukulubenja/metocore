import pytest

from accounts.models import User
from schools.models import School


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.fixture
def teacher(school):
    return User.objects.create_user(
        username="jdoe", password="x", role=User.Role.TEACHER, school=school
    )


@pytest.fixture
def admin(school):
    return User.objects.create_user(
        username="principal", password="x", role=User.Role.ADMIN, school=school
    )


@pytest.mark.django_db
def test_check_in_page_requires_login(client):
    response = client.get("/check-in/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_check_in_page_forbidden_for_admin(client, admin):
    client.force_login(admin)

    response = client.get("/check-in/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_check_in_page_renders_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get("/check-in/")

    assert response.status_code == 200
    assert b"navigator.geolocation" in response.content
    assert b"/api/check-ins/" in response.content
