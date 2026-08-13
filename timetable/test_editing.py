import datetime

import pytest

from accounts.models import User
from schools.models import School
from timetable.models import LessonRequirement, Period, SchoolClass, Subject


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
def period(school):
    return Period.objects.create(
        school=school,
        day_of_week=Period.DayOfWeek.MONDAY,
        name="Morning 1",
        start_time=datetime.time(8, 0),
        end_time=datetime.time(9, 0),
    )


@pytest.fixture
def subject(school):
    return Subject.objects.create(school=school, name="Mathematics", code="MTC")


@pytest.fixture
def school_class(school):
    return SchoolClass.objects.create(school=school, name="S2 EAST")


@pytest.fixture
def requirement(teacher, subject, school_class):
    return LessonRequirement.objects.create(
        teacher=teacher, subject=subject, school_class=school_class, periods_per_week=4
    )


# Period


@pytest.mark.django_db
def test_edit_period_updates_fields(client, school_admin, period):
    client.force_login(school_admin)

    response = client.post(
        f"/timetable/periods/{period.id}/edit/",
        {
            "day_of_week": "1",
            "name": "Morning 1 (renamed)",
            "start_time": "08:30",
            "end_time": "09:30",
            "is_teaching_period": "on",
        },
    )

    assert response.status_code == 302
    period.refresh_from_db()
    assert period.name == "Morning 1 (renamed)"
    assert period.day_of_week == 1


@pytest.mark.django_db
def test_edit_period_forbidden_for_teacher(client, teacher, period):
    client.force_login(teacher)

    response = client.get(f"/timetable/periods/{period.id}/edit/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_edit_period_404_for_other_schools_period(client, school_admin, other_school):
    other_period = Period.objects.create(
        school=other_school,
        day_of_week=Period.DayOfWeek.MONDAY,
        name="Other",
        start_time=datetime.time(8, 0),
        end_time=datetime.time(9, 0),
    )
    client.force_login(school_admin)

    response = client.get(f"/timetable/periods/{other_period.id}/edit/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_period(client, school_admin, period):
    client.force_login(school_admin)

    response = client.post(f"/timetable/periods/{period.id}/delete/")

    assert response.status_code == 302
    assert Period.objects.filter(id=period.id).exists() is False


# Subject


@pytest.mark.django_db
def test_edit_subject_updates_fields(client, school_admin, subject):
    client.force_login(school_admin)

    response = client.post(
        f"/timetable/subjects/{subject.id}/edit/",
        {"name": "Pure Mathematics", "code": "PMTC"},
    )

    assert response.status_code == 302
    subject.refresh_from_db()
    assert subject.name == "Pure Mathematics"
    assert subject.code == "PMTC"


@pytest.mark.django_db
def test_delete_subject(client, school_admin, subject):
    client.force_login(school_admin)

    response = client.post(f"/timetable/subjects/{subject.id}/delete/")

    assert response.status_code == 302
    assert Subject.objects.filter(id=subject.id).exists() is False


# SchoolClass


@pytest.mark.django_db
def test_edit_class_updates_fields(client, school_admin, school_class):
    client.force_login(school_admin)

    response = client.post(
        f"/timetable/classes/{school_class.id}/edit/",
        {"name": "S2 EAST (renamed)", "allows_parallel_lessons": "on"},
    )

    assert response.status_code == 302
    school_class.refresh_from_db()
    assert school_class.name == "S2 EAST (renamed)"
    assert school_class.allows_parallel_lessons is True


@pytest.mark.django_db
def test_delete_class(client, school_admin, school_class):
    client.force_login(school_admin)

    response = client.post(f"/timetable/classes/{school_class.id}/delete/")

    assert response.status_code == 302
    assert SchoolClass.objects.filter(id=school_class.id).exists() is False


# LessonRequirement


@pytest.mark.django_db
def test_edit_requirement_updates_fields(client, school_admin, requirement, teacher, subject, school_class):
    client.force_login(school_admin)

    response = client.post(
        f"/timetable/requirements/{requirement.id}/edit/",
        {
            "teacher_id": teacher.id,
            "subject_id": subject.id,
            "school_class_id": school_class.id,
            "periods_per_week": "6",
        },
    )

    assert response.status_code == 302
    requirement.refresh_from_db()
    assert requirement.periods_per_week == 6


@pytest.mark.django_db
def test_edit_requirement_forbidden_for_teacher(client, teacher, requirement):
    client.force_login(teacher)

    response = client.get(f"/timetable/requirements/{requirement.id}/edit/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_delete_requirement(client, school_admin, requirement):
    client.force_login(school_admin)

    response = client.post(f"/timetable/requirements/{requirement.id}/delete/")

    assert response.status_code == 302
    assert LessonRequirement.objects.filter(id=requirement.id).exists() is False
