import pytest

from accounts.models import User
from attendance.models import CheckIn
from schools.models import Geofence, School


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


@pytest.mark.django_db
def test_check_in_page_shows_checkout_button_after_confirmed_checkin(client, teacher, school):
    geofence = Geofence.objects.create(
        school=school,
        name="Main Campus",
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=200,
    )
    CheckIn.objects.create(
        teacher=teacher,
        geofence=geofence,
        latitude=0.001,
        longitude=0.0,
        gps_accuracy_m=15,
        distance_m=10,
        status=CheckIn.Status.CONFIRMED,
        reason="Within range.",
    )
    client.force_login(teacher)

    response = client.get("/check-in/")

    assert response.status_code == 200
    assert b"/api/check-outs/" in response.content
    assert b"Check Out Now" in response.content


@pytest.mark.django_db
def test_check_in_page_shows_summary_after_checkout(client, teacher, school):
    geofence = Geofence.objects.create(
        school=school,
        name="Main Campus",
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=200,
    )
    check_in = CheckIn.objects.create(
        teacher=teacher,
        geofence=geofence,
        latitude=0.001,
        longitude=0.0,
        gps_accuracy_m=15,
        distance_m=10,
        status=CheckIn.Status.CONFIRMED,
        reason="Within range.",
    )
    check_in.record_checkout(latitude=0.001, longitude=0.0, gps_accuracy_m=15)
    client.force_login(teacher)

    response = client.get("/check-in/")

    assert response.status_code == 200
    assert b"Checked out at" in response.content
    assert b"Check Out Now" not in response.content
