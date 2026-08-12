import pytest
from rest_framework.test import APIClient

from accounts.models import User
from attendance.models import CheckIn
from schools.models import Geofence, School


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


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
def teacher(school):
    return User.objects.create_user(
        username="jdoe", password="x", role=User.Role.TEACHER, school=school
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_teacher_can_check_in_successfully(api_client, teacher, geofence):
    api_client.force_authenticate(user=teacher)

    response = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == CheckIn.Status.CONFIRMED
    assert response.data["reason"] != ""
    assert CheckIn.objects.count() == 1


@pytest.mark.django_db
def test_unauthenticated_request_rejected(api_client):
    response = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_non_teacher_role_rejected(api_client, school):
    admin = User.objects.create_user(
        username="principal", password="x", role=User.Role.ADMIN, school=school
    )
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_teacher_without_school_gets_clear_error(api_client):
    teacher = User.objects.create_user(username="jdoe", password="x", role=User.Role.TEACHER)
    api_client.force_authenticate(user=teacher)

    response = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )

    assert response.status_code == 400
    assert "school" in response.data["detail"].lower()


@pytest.mark.django_db
def test_teacher_with_school_but_no_geofences_gets_clear_error(api_client, school):
    teacher = User.objects.create_user(
        username="jdoe", password="x", role=User.Role.TEACHER, school=school
    )
    api_client.force_authenticate(user=teacher)

    response = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )

    assert response.status_code == 400
    assert "check-in zone" in response.data["detail"].lower()


@pytest.mark.django_db
def test_invalid_latitude_rejected(api_client, teacher, geofence):
    api_client.force_authenticate(user=teacher)

    response = api_client.post(
        "/api/check-ins/",
        {"latitude": 999, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_second_confirmed_checkin_same_day_rejected(api_client, teacher, geofence):
    api_client.force_authenticate(user=teacher)

    first = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )
    assert first.status_code == 201
    assert first.data["status"] == CheckIn.Status.CONFIRMED

    second = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )

    assert second.status_code == 400
    assert "already checked in" in second.data["detail"].lower()
    assert CheckIn.objects.count() == 1


@pytest.mark.django_db
def test_needs_review_checkin_allowed_after_earlier_confirmed_checkin(api_client, teacher, geofence):
    api_client.force_authenticate(user=teacher)

    first = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )
    assert first.status_code == 201
    assert first.data["status"] == CheckIn.Status.CONFIRMED

    second = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 150},
        format="json",
    )

    assert second.status_code == 201
    assert second.data["status"] == CheckIn.Status.NEEDS_REVIEW
    assert CheckIn.objects.count() == 2


@pytest.mark.django_db
def test_checks_in_against_nearest_geofence_when_multiple_exist(api_client, teacher, school, geofence):
    far_geofence = Geofence.objects.create(
        school=school,
        name="Annex",
        center_latitude=5.0,
        center_longitude=5.0,
        radius_m=200,
    )
    api_client.force_authenticate(user=teacher)

    response = api_client.post(
        "/api/check-ins/",
        {"latitude": 0.001, "longitude": 0.0, "gps_accuracy_m": 15},
        format="json",
    )

    assert response.status_code == 201
    check_in = CheckIn.objects.get(pk=response.data["id"])
    assert check_in.geofence == geofence
    assert check_in.geofence != far_geofence
