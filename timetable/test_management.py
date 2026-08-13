import datetime

import pytest

from accounts.models import User
from schools.models import School
from timetable.models import LessonRequirement, Period, SchoolClass, Subject, TeacherAvailability


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


@pytest.mark.django_db
def test_manage_periods_requires_login(client):
    response = client.get("/timetable/periods/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_manage_periods_forbidden_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get("/timetable/periods/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_creating_period_via_post(client, school_admin, school):
    client.force_login(school_admin)

    response = client.post(
        "/timetable/periods/",
        {
            "day_of_week": "0",
            "name": "Morning 1",
            "start_time": "08:00",
            "end_time": "09:20",
            "is_teaching_period": "on",
        },
    )

    assert response.status_code == 302
    created = Period.objects.get(name="Morning 1")
    assert created.school == school
    assert created.is_teaching_period is True


@pytest.mark.django_db
def test_creating_period_with_end_before_start_shows_error(client, school_admin):
    client.force_login(school_admin)

    response = client.post(
        "/timetable/periods/",
        {
            "day_of_week": "0",
            "name": "Bad period",
            "start_time": "09:20",
            "end_time": "08:00",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert Period.objects.filter(name="Bad period").exists() is False


@pytest.mark.django_db
def test_periods_scoped_to_own_school(client, school_admin, period, other_school):
    Period.objects.create(
        school=other_school,
        day_of_week=Period.DayOfWeek.MONDAY,
        name="Other school period",
        start_time=datetime.time(8, 0),
        end_time=datetime.time(9, 0),
    )
    client.force_login(school_admin)

    response = client.get("/timetable/periods/")

    assert response.status_code == 200
    assert b"Other school period" not in response.content


@pytest.mark.django_db
def test_creating_subject_via_post(client, school_admin, school):
    client.force_login(school_admin)

    response = client.post(
        "/timetable/subjects/", {"name": "Physics", "code": "PHY"}
    )

    assert response.status_code == 302
    assert Subject.objects.get(code="PHY").school == school


@pytest.mark.django_db
def test_manage_subjects_forbidden_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get("/timetable/subjects/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_creating_class_via_post(client, school_admin, school):
    client.force_login(school_admin)

    response = client.post(
        "/timetable/classes/", {"name": "S.5", "allows_parallel_lessons": "on"}
    )

    assert response.status_code == 302
    created = SchoolClass.objects.get(name="S.5")
    assert created.allows_parallel_lessons is True


@pytest.mark.django_db
def test_setting_teacher_availability(client, school_admin, teacher, period):
    client.force_login(school_admin)

    response = client.post(
        "/timetable/availability/",
        {"teacher_id": teacher.id, "period_ids": [period.id]},
    )

    assert response.status_code == 302
    assert TeacherAvailability.objects.filter(teacher=teacher, period=period).exists()


@pytest.mark.django_db
def test_availability_forbidden_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get("/timetable/availability/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_creating_lesson_requirement(client, school_admin, teacher, subject, school_class):
    client.force_login(school_admin)

    response = client.post(
        "/timetable/requirements/",
        {
            "teacher_id": teacher.id,
            "subject_id": subject.id,
            "school_class_id": school_class.id,
            "periods_per_week": "4",
        },
    )

    assert response.status_code == 302
    created = LessonRequirement.objects.get()
    assert created.teacher == teacher
    assert created.periods_per_week == 4


@pytest.mark.django_db
def test_lesson_requirement_with_invalid_count_shows_error(
    client, school_admin, teacher, subject, school_class
):
    client.force_login(school_admin)

    response = client.post(
        "/timetable/requirements/",
        {
            "teacher_id": teacher.id,
            "subject_id": subject.id,
            "school_class_id": school_class.id,
            "periods_per_week": "0",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert LessonRequirement.objects.exists() is False


@pytest.mark.django_db
def test_requirement_for_other_schools_teacher_404s(client, school_admin, other_school, subject, school_class):
    other_teacher = User.objects.create_user(
        username="other", password="x", role=User.Role.TEACHER, school=other_school
    )
    client.force_login(school_admin)

    response = client.post(
        "/timetable/requirements/",
        {
            "teacher_id": other_teacher.id,
            "subject_id": subject.id,
            "school_class_id": school_class.id,
            "periods_per_week": "2",
        },
    )

    assert response.status_code == 404
