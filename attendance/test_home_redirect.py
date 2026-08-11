import pytest

from accounts.models import User
from schools.models import School


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.mark.django_db
def test_home_requires_login(client):
    response = client.get("/home/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_home_redirects_teacher_to_check_in_page(client, school):
    teacher = User.objects.create_user(
        username="jdoe", password="x", role=User.Role.TEACHER, school=school
    )
    client.force_login(teacher)

    response = client.get("/home/")

    assert response.status_code == 302
    assert response.url == "/check-in/"


@pytest.mark.django_db
def test_home_redirects_school_admin_to_dashboard(client, school):
    admin = User.objects.create_user(
        username="principal", password="x", role=User.Role.ADMIN, school=school
    )
    client.force_login(admin)

    response = client.get("/home/")

    assert response.status_code == 302
    assert response.url == "/dashboard/"


@pytest.mark.django_db
def test_home_redirects_superuser_to_platform_schools(client):
    superuser = User.objects.create_superuser(
        username="platform", password="x", email="p@example.com"
    )
    client.force_login(superuser)

    response = client.get("/home/")

    assert response.status_code == 302
    assert response.url == "/platform/schools/"


@pytest.mark.django_db
def test_home_prioritizes_superuser_over_school_admin_role(client, school):
    superuser_admin = User.objects.create_superuser(
        username="platform", password="x", email="p@example.com", role=User.Role.ADMIN, school=school
    )
    client.force_login(superuser_admin)

    response = client.get("/home/")

    assert response.status_code == 302
    assert response.url == "/platform/schools/"
