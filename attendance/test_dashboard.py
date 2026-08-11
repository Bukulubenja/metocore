import pytest
from django.utils import timezone

from accounts.models import User
from attendance.models import CheckIn
from schools.models import Geofence, School


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.fixture
def other_school():
    return School.objects.create(name="Hillcrest Academy")


@pytest.fixture
def geofence(school):
    return Geofence.objects.create(
        school=school,
        name="Main Campus",
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=200,
    )


@pytest.fixture
def admin(school):
    return User.objects.create_user(
        username="principal", password="x", role=User.Role.ADMIN, school=school
    )


@pytest.fixture
def teacher(school):
    return User.objects.create_user(
        username="jdoe", password="x", role=User.Role.TEACHER, school=school
    )


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get("/dashboard/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_teacher_cannot_access_dashboard(client, teacher):
    client.force_login(teacher)

    response = client.get("/dashboard/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_sees_todays_checkins_with_status_and_reason(client, admin, teacher, geofence):
    CheckIn.create_from_location(
        teacher=teacher, geofence=geofence, latitude=0.001, longitude=0.0, gps_accuracy_m=15
    )
    client.force_login(admin)

    response = client.get("/dashboard/")

    assert response.status_code == 200
    assert b"jdoe" in response.content
    assert b"Confirmed" in response.content
    assert b"geofence" in response.content  # part of the explainable reason text


@pytest.mark.django_db
def test_admin_does_not_see_other_schools_checkins(
    client, admin, other_school, geofence
):
    other_geofence = Geofence.objects.create(
        school=other_school,
        name="Other Campus",
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=200,
    )
    other_teacher = User.objects.create_user(
        username="msmith", password="x", role=User.Role.TEACHER, school=other_school
    )
    CheckIn.create_from_location(
        teacher=other_teacher,
        geofence=other_geofence,
        latitude=0.001,
        longitude=0.0,
        gps_accuracy_m=15,
    )
    client.force_login(admin)

    response = client.get("/dashboard/")

    assert b"msmith" not in response.content


@pytest.mark.django_db
def test_admin_does_not_see_yesterdays_checkins(client, admin, teacher, geofence):
    check_in = CheckIn.create_from_location(
        teacher=teacher, geofence=geofence, latitude=0.001, longitude=0.0, gps_accuracy_m=15
    )
    check_in.checked_in_at = timezone.now() - timezone.timedelta(days=1)
    check_in.save()
    client.force_login(admin)

    response = client.get("/dashboard/")

    assert b"jdoe" not in response.content
