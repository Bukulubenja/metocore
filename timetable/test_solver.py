import datetime

import pytest

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
from timetable.solver import TimetableGenerationError, generate_timetable


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.fixture
def term(school):
    return Term.objects.create(
        school=school,
        academic_year="2025/2026",
        name="Term 1",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 3, 1),
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
            day_of_week=day,
            name=f"Period {slot}",
            start_time=datetime.time(8 + slot, 0),
            end_time=datetime.time(9 + slot, 0),
        )
        for day in range(2)
        for slot in range(2)
    ]


@pytest.fixture
def subject(school):
    return Subject.objects.create(school=school, name="Mathematics", code="MTC")


@pytest.fixture
def other_subject(school):
    return Subject.objects.create(school=school, name="Physics", code="PHY")


@pytest.fixture
def exclusive_class(school):
    return SchoolClass.objects.create(school=school, name="S2 EAST")


@pytest.fixture
def parallel_class(school):
    return SchoolClass.objects.create(
        school=school, name="S.5", allows_parallel_lessons=True
    )


def _make_available(teacher, periods_qs):
    for period in periods_qs:
        TeacherAvailability.objects.create(teacher=teacher, period=period)


@pytest.mark.django_db
def test_generates_entries_matching_periods_per_week(
    school, term, teacher_a, periods, subject, exclusive_class
):
    _make_available(teacher_a, periods)
    LessonRequirement.objects.create(
        teacher=teacher_a, subject=subject, school_class=exclusive_class, periods_per_week=2
    )

    entries = generate_timetable(school=school, term=term)

    assert len(entries) == 2
    assert TimetableEntry.objects.filter(term=term).count() == 2


@pytest.mark.django_db
def test_never_double_books_a_teacher(
    school, term, teacher_a, periods, subject, other_subject, exclusive_class, parallel_class
):
    _make_available(teacher_a, periods)
    LessonRequirement.objects.create(
        teacher=teacher_a, subject=subject, school_class=exclusive_class, periods_per_week=2
    )
    LessonRequirement.objects.create(
        teacher=teacher_a, subject=other_subject, school_class=parallel_class, periods_per_week=2
    )

    entries = generate_timetable(school=school, term=term)

    period_ids = [entry.period_id for entry in entries]
    assert len(period_ids) == len(set(period_ids))


@pytest.mark.django_db
def test_exclusive_class_cannot_double_book(
    school, term, teacher_a, teacher_b, periods, subject, other_subject, exclusive_class
):
    _make_available(teacher_a, periods)
    _make_available(teacher_b, periods)
    LessonRequirement.objects.create(
        teacher=teacher_a, subject=subject, school_class=exclusive_class, periods_per_week=2
    )
    LessonRequirement.objects.create(
        teacher=teacher_b, subject=other_subject, school_class=exclusive_class, periods_per_week=2
    )

    generate_timetable(school=school, term=term)

    for period in periods:
        assert TimetableEntry.objects.filter(
            term=term, school_class=exclusive_class, period=period
        ).count() <= 1


@pytest.mark.django_db
def test_parallel_class_allows_simultaneous_lessons(
    school, term, teacher_a, teacher_b, periods, subject, other_subject, parallel_class
):
    _make_available(teacher_a, periods)
    _make_available(teacher_b, periods)
    LessonRequirement.objects.create(
        teacher=teacher_a, subject=subject, school_class=parallel_class, periods_per_week=4
    )
    LessonRequirement.objects.create(
        teacher=teacher_b, subject=other_subject, school_class=parallel_class, periods_per_week=4
    )

    generate_timetable(school=school, term=term)

    assert TimetableEntry.objects.filter(term=term, school_class=parallel_class).count() == 8


@pytest.mark.django_db
def test_raises_clear_error_when_teacher_lacks_availability(
    school, term, teacher_a, periods, subject, exclusive_class
):
    _make_available(teacher_a, periods[:1])
    LessonRequirement.objects.create(
        teacher=teacher_a, subject=subject, school_class=exclusive_class, periods_per_week=2
    )

    with pytest.raises(TimetableGenerationError, match="enough available periods"):
        generate_timetable(school=school, term=term)


@pytest.mark.django_db
def test_raises_when_no_requirements_exist(school, term):
    with pytest.raises(TimetableGenerationError, match="No lesson requirements"):
        generate_timetable(school=school, term=term)


@pytest.mark.django_db
def test_regenerating_replaces_previous_entries(
    school, term, teacher_a, periods, subject, exclusive_class
):
    _make_available(teacher_a, periods)
    LessonRequirement.objects.create(
        teacher=teacher_a, subject=subject, school_class=exclusive_class, periods_per_week=2
    )

    generate_timetable(school=school, term=term)
    generate_timetable(school=school, term=term)

    assert TimetableEntry.objects.filter(term=term).count() == 2
