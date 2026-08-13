import datetime

import pytest
from django.utils import timezone

from accounts.models import User
from schools.models import School, Term


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
def term(school):
    today = timezone.localdate()
    return Term.objects.create(
        school=school,
        academic_year="2025/2026",
        name="Term 1",
        start_date=today - datetime.timedelta(days=10),
        end_date=today + datetime.timedelta(days=10),
    )


@pytest.mark.django_db
def test_manage_terms_requires_login(client):
    response = client.get("/terms/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_manage_terms_forbidden_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get("/terms/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_manage_terms_shows_only_own_schools_terms(client, school_admin, term, other_school):
    Term.objects.create(
        school=other_school,
        academic_year="2025/2026",
        name="Term 1",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 3, 1),
    )
    client.force_login(school_admin)

    response = client.get("/terms/")

    assert response.status_code == 200
    assert b"Term 1" in response.content


@pytest.mark.django_db
def test_creating_term_via_post(client, school_admin, school):
    client.force_login(school_admin)

    response = client.post(
        "/terms/",
        {
            "academic_year": "2025/2026",
            "name": "Term 2",
            "start_date": "2026-05-01",
            "end_date": "2026-08-01",
        },
    )

    assert response.status_code == 302
    created = Term.objects.get(name="Term 2")
    assert created.school == school
    assert created.academic_year == "2025/2026"


@pytest.mark.django_db
def test_creating_term_with_end_before_start_shows_error(client, school_admin):
    client.force_login(school_admin)

    response = client.post(
        "/terms/",
        {
            "academic_year": "2025/2026",
            "name": "Term 2",
            "start_date": "2026-08-01",
            "end_date": "2026-05-01",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert Term.objects.filter(name="Term 2").exists() is False
    assert b"on or after" in response.content


@pytest.mark.django_db
def test_edit_term_updates_fields(client, school_admin, term):
    client.force_login(school_admin)

    response = client.post(
        f"/terms/{term.id}/edit/",
        {
            "academic_year": "2025/2026",
            "name": "Term 1 (renamed)",
            "start_date": "2026-01-01",
            "end_date": "2026-03-01",
        },
    )

    assert response.status_code == 302
    term.refresh_from_db()
    assert term.name == "Term 1 (renamed)"


@pytest.mark.django_db
def test_edit_term_404_for_other_schools_term(client, school_admin, other_school):
    other_term = Term.objects.create(
        school=other_school,
        academic_year="2025/2026",
        name="Term 1",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 3, 1),
    )
    client.force_login(school_admin)

    response = client.get(f"/terms/{other_term.id}/edit/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_term_is_current_for_dates_spanning_today(term):
    assert term.is_current is True


@pytest.mark.django_db
def test_term_is_current_false_for_past_term(school):
    past_term = Term.objects.create(
        school=school,
        academic_year="2024/2025",
        name="Term 3",
        start_date=datetime.date(2025, 1, 1),
        end_date=datetime.date(2025, 3, 1),
    )

    assert past_term.is_current is False


@pytest.mark.django_db
def test_current_for_returns_the_active_term(school, term):
    past_term = Term.objects.create(
        school=school,
        academic_year="2024/2025",
        name="Term 3",
        start_date=datetime.date(2025, 1, 1),
        end_date=datetime.date(2025, 3, 1),
    )

    current = Term.objects.current_for(school)

    assert current == term
    assert current != past_term
