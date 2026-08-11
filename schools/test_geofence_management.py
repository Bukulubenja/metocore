import pytest

from accounts.models import User
from schools.models import Geofence, School


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
def geofence(school):
    return Geofence.objects.create(
        school=school,
        name="Main Campus",
        center_latitude=6.5244,
        center_longitude=3.3792,
        radius_m=150,
    )


@pytest.mark.django_db
def test_manage_geofences_requires_login(client):
    response = client.get("/geofences/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_manage_geofences_forbidden_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get("/geofences/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_manage_geofences_shows_only_own_schools_geofences(
    client, school_admin, geofence, other_school
):
    Geofence.objects.create(
        school=other_school,
        name="Other Campus",
        center_latitude=0,
        center_longitude=0,
        radius_m=100,
    )
    client.force_login(school_admin)

    response = client.get("/geofences/")

    assert response.status_code == 200
    assert b"Main Campus" in response.content
    assert b"Other Campus" not in response.content


@pytest.mark.django_db
def test_creating_geofence_via_post(client, school_admin, school):
    client.force_login(school_admin)

    response = client.post(
        "/geofences/",
        {
            "name": "Annex",
            "center_latitude": "6.5300",
            "center_longitude": "3.3800",
            "radius_m": "100",
        },
    )

    assert response.status_code == 302
    created = Geofence.objects.get(name="Annex")
    assert created.school == school
    assert created.radius_m == 100


@pytest.mark.django_db
def test_creating_geofence_with_invalid_latitude_shows_error(client, school_admin):
    client.force_login(school_admin)

    response = client.post(
        "/geofences/",
        {
            "name": "Annex",
            "center_latitude": "999",
            "center_longitude": "3.3800",
            "radius_m": "100",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert Geofence.objects.filter(name="Annex").exists() is False
    assert b"Latitude" in response.content


@pytest.mark.django_db
def test_creating_geofence_with_non_numeric_radius_shows_error(client, school_admin):
    client.force_login(school_admin)

    response = client.post(
        "/geofences/",
        {
            "name": "Annex",
            "center_latitude": "6.5300",
            "center_longitude": "3.3800",
            "radius_m": "not-a-number",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert Geofence.objects.filter(name="Annex").exists() is False


@pytest.mark.django_db
def test_edit_geofence_page_requires_school_admin(client, teacher, geofence):
    client.force_login(teacher)

    response = client.get(f"/geofences/{geofence.id}/edit/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_edit_geofence_updates_fields(client, school_admin, geofence):
    client.force_login(school_admin)

    response = client.post(
        f"/geofences/{geofence.id}/edit/",
        {
            "name": "Main Campus (renamed)",
            "center_latitude": "6.5250",
            "center_longitude": "3.3799",
            "radius_m": "175",
        },
    )

    assert response.status_code == 302
    geofence.refresh_from_db()
    assert geofence.name == "Main Campus (renamed)"
    assert geofence.radius_m == 175


@pytest.mark.django_db
def test_edit_geofence_404_for_other_schools_geofence(client, school_admin, other_school):
    other_geofence = Geofence.objects.create(
        school=other_school,
        name="Other Campus",
        center_latitude=0,
        center_longitude=0,
        radius_m=100,
    )
    client.force_login(school_admin)

    response = client.get(f"/geofences/{other_geofence.id}/edit/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_edit_geofence_with_invalid_data_does_not_change_existing_values(
    client, school_admin, geofence
):
    original_radius = geofence.radius_m
    client.force_login(school_admin)

    client.post(
        f"/geofences/{geofence.id}/edit/",
        {
            "name": "Main Campus",
            "center_latitude": "6.5244",
            "center_longitude": "3.3792",
            "radius_m": "-5",
        },
    )

    geofence.refresh_from_db()
    assert geofence.radius_m == original_radius
