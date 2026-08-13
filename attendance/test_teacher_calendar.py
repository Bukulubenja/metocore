import datetime

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
def school_admin(school):
    return User.objects.create_user(
        username="principal", password="x", role=User.Role.ADMIN, school=school
    )


@pytest.fixture
def teacher(school):
    return User.objects.create_user(
        username="jdoe", password="x", role=User.Role.TEACHER, school=school
    )


@pytest.mark.django_db
def test_teacher_calendar_requires_login(client, teacher):
    response = client.get(f"/teachers/{teacher.id}/calendar/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_teacher_calendar_forbidden_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get(f"/teachers/{teacher.id}/calendar/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_teacher_calendar_404_for_other_schools_teacher(
    client, school_admin, other_school
):
    other_teacher = User.objects.create_user(
        username="other", password="x", role=User.Role.TEACHER, school=other_school
    )
    client.force_login(school_admin)

    response = client.get(f"/teachers/{other_teacher.id}/calendar/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_teacher_calendar_shows_confirmed_day(client, school_admin, teacher, geofence):
    today = timezone.localdate()
    CheckIn.objects.create(
        teacher=teacher,
        geofence=geofence,
        latitude=0.001,
        longitude=0.0,
        gps_accuracy_m=15,
        distance_m=10,
        status=CheckIn.Status.CONFIRMED,
        reason="Within range.",
        checked_in_at=timezone.now(),
    )
    client.force_login(school_admin)

    response = client.get(
        f"/teachers/{teacher.id}/calendar/?year={today.year}&month={today.month}"
    )

    assert response.status_code == 200
    assert str(today.day).encode() in response.content
    assert b"Present" in response.content


@pytest.mark.django_db
def test_teacher_calendar_confirmed_takes_priority_over_needs_review_same_day(
    client, school_admin, teacher, geofence
):
    today = timezone.now()
    CheckIn.objects.create(
        teacher=teacher,
        geofence=geofence,
        latitude=0.001,
        longitude=0.0,
        gps_accuracy_m=15,
        distance_m=10,
        status=CheckIn.Status.NEEDS_REVIEW,
        reason="Low accuracy.",
        checked_in_at=today,
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
        checked_in_at=today,
    )
    client.force_login(school_admin)

    response = client.get(
        f"/teachers/{teacher.id}/calendar/?year={today.year}&month={today.month}"
    )

    assert response.status_code == 200
    assert b"Present" in response.content
    assert b"Review" not in response.content


@pytest.mark.django_db
def test_teacher_calendar_month_navigation_params(client, school_admin, teacher):
    client.force_login(school_admin)

    response = client.get(f"/teachers/{teacher.id}/calendar/?year=2026&month=3")

    assert response.status_code == 200
    assert b"March 2026" in response.content
