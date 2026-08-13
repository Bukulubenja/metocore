import datetime

import pytest
from django.utils import timezone

from accounts.models import User
from attendance.models import CheckIn
from schools.models import Geofence, School, Term


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
        username="jdoe", password="x", role=User.Role.TEACHER, school=school, title="Class Teacher"
    )


def _confirmed_checkin(teacher, geofence, when):
    return CheckIn.objects.create(
        teacher=teacher,
        geofence=geofence,
        latitude=0.001,
        longitude=0.0,
        gps_accuracy_m=15,
        distance_m=10,
        status=CheckIn.Status.CONFIRMED,
        reason="Within range.",
        checked_in_at=when,
    )


@pytest.mark.django_db
def test_attendance_report_requires_login(client):
    response = client.get("/reports/attendance/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_attendance_report_forbidden_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get("/reports/attendance/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_report_counts_confirmed_checkins_in_manual_range(
    client, school_admin, teacher, geofence
):
    _confirmed_checkin(teacher, geofence, timezone.make_aware(datetime.datetime(2026, 2, 5)))
    _confirmed_checkin(teacher, geofence, timezone.make_aware(datetime.datetime(2026, 2, 10)))
    _confirmed_checkin(teacher, geofence, timezone.make_aware(datetime.datetime(2026, 3, 1)))
    client.force_login(school_admin)

    response = client.get(
        "/reports/attendance/?start_date=2026-02-01&end_date=2026-02-28"
    )

    assert response.status_code == 200
    assert b"2" in response.content
    assert b"Class Teacher" in response.content


@pytest.mark.django_db
def test_report_uses_term_dates_and_labels(client, school_admin, school, teacher, geofence):
    term = Term.objects.create(
        school=school,
        academic_year="2025/2026",
        name="Term 1",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 3, 1),
    )
    _confirmed_checkin(teacher, geofence, timezone.make_aware(datetime.datetime(2026, 1, 15)))
    client.force_login(school_admin)

    response = client.get(f"/reports/attendance/?term_id={term.id}")

    assert response.status_code == 200
    assert b"2025/2026" in response.content
    assert b"Term 1" in response.content


@pytest.mark.django_db
def test_report_excludes_other_schools_teachers(
    client, school_admin, school, other_school, geofence
):
    other_teacher = User.objects.create_user(
        username="other", password="x", role=User.Role.TEACHER, school=other_school
    )
    client.force_login(school_admin)

    response = client.get(
        "/reports/attendance/?start_date=2026-01-01&end_date=2026-12-31"
    )

    assert response.status_code == 200
    assert b"other" not in response.content


@pytest.mark.django_db
def test_export_returns_csv_attachment(client, school_admin, teacher, geofence):
    _confirmed_checkin(teacher, geofence, timezone.make_aware(datetime.datetime(2026, 2, 5)))
    client.force_login(school_admin)

    response = client.get(
        "/reports/attendance/export/?start_date=2026-02-01&end_date=2026-02-28"
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert "attachment" in response["Content-Disposition"]
    content = response.content.decode()
    assert "jdoe" in content
    assert "Class Teacher" in content
    assert "Riverside Primary" in content
    assert "1" in content


@pytest.mark.django_db
def test_export_forbidden_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get(
        "/reports/attendance/export/?start_date=2026-02-01&end_date=2026-02-28"
    )

    assert response.status_code == 403
