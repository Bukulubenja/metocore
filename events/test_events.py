import datetime

import pytest
from django.utils import timezone

from accounts.models import User
from events.models import Event
from schools.models import School


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
def upcoming_event(school):
    return Event.objects.create(
        school=school,
        title="Sports day",
        date=timezone.localdate() + datetime.timedelta(days=5),
    )


@pytest.fixture
def past_event(school):
    return Event.objects.create(
        school=school,
        title="Term 1 assembly",
        date=timezone.localdate() - datetime.timedelta(days=5),
    )


@pytest.mark.django_db
def test_event_list_requires_login(client):
    response = client.get("/events/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_teacher_can_view_events_split_by_upcoming_and_past(
    client, teacher, upcoming_event, past_event
):
    client.force_login(teacher)

    response = client.get("/events/")

    assert response.status_code == 200
    assert b"Sports day" in response.content
    assert b"Term 1 assembly" in response.content


@pytest.mark.django_db
def test_teacher_cannot_create_event(client, teacher):
    client.force_login(teacher)

    response = client.post("/events/", {"title": "Fake", "date": "2026-12-01"})

    assert response.status_code == 403
    assert Event.objects.filter(title="Fake").exists() is False


@pytest.mark.django_db
def test_admin_can_create_event(client, school_admin, school):
    client.force_login(school_admin)

    response = client.post(
        "/events/",
        {"title": "Sports day", "date": "2026-12-01", "location": "Main field"},
    )

    assert response.status_code == 302
    created = Event.objects.get(title="Sports day")
    assert created.school == school
    assert created.location == "Main field"


@pytest.mark.django_db
def test_creating_event_with_invalid_date_shows_error(client, school_admin):
    client.force_login(school_admin)

    response = client.post(
        "/events/", {"title": "Sports day", "date": "not-a-date"}, follow=True
    )

    assert response.status_code == 200
    assert Event.objects.filter(title="Sports day").exists() is False


@pytest.mark.django_db
def test_admin_can_delete_event(client, school_admin, upcoming_event):
    client.force_login(school_admin)

    response = client.post(f"/events/{upcoming_event.id}/delete/")

    assert response.status_code == 302
    assert Event.objects.filter(id=upcoming_event.id).exists() is False


@pytest.mark.django_db
def test_teacher_cannot_delete_event(client, teacher, upcoming_event):
    client.force_login(teacher)

    response = client.post(f"/events/{upcoming_event.id}/delete/")

    assert response.status_code == 403
    assert Event.objects.filter(id=upcoming_event.id).exists() is True


@pytest.mark.django_db
def test_events_scoped_to_own_school(client, school_admin, other_school):
    Event.objects.create(
        school=other_school, title="Other school event", date=timezone.localdate()
    )
    client.force_login(school_admin)

    response = client.get("/events/")

    assert response.status_code == 200
    assert b"Other school event" not in response.content
