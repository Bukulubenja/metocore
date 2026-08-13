import datetime

import pytest
from django.utils import timezone

from accounts.models import User
from schools.models import School, Term
from timetable.models import (
    LessonRequirement,
    Period,
    SchoolClass,
    Subject,
    TeacherAvailability,
    TimetableEntry,
)


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.fixture
def term(school):
    today = timezone.localdate()
    return Term.objects.create(
        school=school,
        academic_year="2025/2026",
        name="Term 1",
        start_date=today - datetime.timedelta(days=10),
        end_date=today + datetime.timedelta(days=10),
    )


@pytest.fixture
def school_admin(school):
    return User.objects.create_user(
        username="principal", password="x", role=User.Role.ADMIN, school=school
    )


@pytest.fixture
def teacher_a(school):
    return User.objects.create_user(
        username="jdoe", password="x", role=User.Role.TEACHER, school=school
    )


@pytest.fixture
def teacher_b(school):
    return User.objects.create_user(
        username="asmith", password="x", role=User.Role.TEACHER, school=school
    )


@pytest.fixture
def periods(school):
    return [
        Period.objects.create(
            school=school,
            day_of_week=Period.DayOfWeek.MONDAY,
            name=f"Period {slot}",
            start_time=datetime.time(8 + slot, 0),
            end_time=datetime.time(9 + slot, 0),
        )
        for slot in range(2)
    ]


@pytest.fixture
def subject(school):
    return Subject.objects.create(school=school, name="Mathematics", code="MTC")


@pytest.fixture
def other_subject(school):
    return Subject.objects.create(school=school, name="Physics", code="PHY")


@pytest.fixture
def school_class(school):
    return SchoolClass.objects.create(school=school, name="S2 EAST")


@pytest.mark.django_db
def test_generate_view_creates_timetable_entries(
    client, school_admin, term, teacher_a, periods, subject, school_class
):
    for period in periods:
        TeacherAvailability.objects.create(teacher=teacher_a, period=period)
    LessonRequirement.objects.create(
        teacher=teacher_a, subject=subject, school_class=school_class, periods_per_week=2
    )
    client.force_login(school_admin)

    response = client.post("/timetable/generate/", {"term_id": term.id})

    assert response.status_code == 302
    assert TimetableEntry.objects.filter(term=term).count() == 2


@pytest.mark.django_db
def test_generate_view_forbidden_for_teacher(client, teacher_a, term):
    client.force_login(teacher_a)

    response = client.post("/timetable/generate/", {"term_id": term.id})

    assert response.status_code == 403


@pytest.mark.django_db
def test_generate_view_shows_error_when_infeasible(client, school_admin, term, teacher_a, subject, school_class):
    LessonRequirement.objects.create(
        teacher=teacher_a, subject=subject, school_class=school_class, periods_per_week=2
    )
    client.force_login(school_admin)

    response = client.post("/timetable/generate/", {"term_id": term.id}, follow=True)

    assert response.status_code == 200
    assert TimetableEntry.objects.filter(term=term).exists() is False


@pytest.mark.django_db
def test_manual_edit_rejects_double_booking_a_teacher(
    client, school_admin, term, teacher_a, teacher_b, periods, subject, other_subject, school_class
):
    other_class = SchoolClass.objects.create(school=school_class.school, name="S2 WEST")
    entry_one = TimetableEntry.objects.create(
        term=term, school_class=school_class, period=periods[0], subject=subject, teacher=teacher_a
    )
    TimetableEntry.objects.create(
        term=term, school_class=other_class, period=periods[0], subject=other_subject, teacher=teacher_b
    )
    client.force_login(school_admin)

    response = client.post(
        f"/timetable/entries/{entry_one.id}/edit/",
        {"teacher_id": teacher_b.id, "subject_id": subject.id},
        follow=True,
    )

    assert response.status_code == 200
    entry_one.refresh_from_db()
    assert entry_one.teacher == teacher_a


@pytest.mark.django_db
def test_timetable_view_requires_school_admin(client, teacher_a):
    client.force_login(teacher_a)

    response = client.get("/timetable/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_my_timetable_shows_only_own_lessons(
    client, teacher_a, teacher_b, term, periods, subject, other_subject, school_class
):
    TimetableEntry.objects.create(
        term=term, school_class=school_class, period=periods[0], subject=subject, teacher=teacher_a
    )
    TimetableEntry.objects.create(
        term=term, school_class=school_class, period=periods[1], subject=other_subject, teacher=teacher_b
    )
    client.force_login(teacher_a)

    response = client.get("/my-timetable/")

    assert response.status_code == 200
    assert b"MTC" in response.content
    assert b"PHY" not in response.content
