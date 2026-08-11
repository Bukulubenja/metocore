import pytest

from schools.geo import distance_meters
from schools.models import Geofence, School


def test_distance_meters_zero_for_identical_points():
    assert distance_meters(0.0, 0.0, 0.0, 0.0) == pytest.approx(0.0, abs=0.01)


def test_distance_meters_matches_known_haversine_distance():
    # 0.001 degrees of latitude is ~111 meters.
    distance = distance_meters(0.0, 0.0, 0.001, 0.0)

    assert distance == pytest.approx(111.19, abs=1.0)


@pytest.mark.django_db
def test_school_str_returns_name():
    school = School.objects.create(name="Riverside Primary")

    assert str(school) == "Riverside Primary"


@pytest.mark.django_db
def test_geofence_contains_point_true_when_within_radius():
    school = School.objects.create(name="Riverside Primary")
    geofence = Geofence.objects.create(
        school=school,
        name="Main Campus",
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=200,
    )

    assert geofence.contains_point(0.001, 0.0) is True


@pytest.mark.django_db
def test_geofence_contains_point_false_when_outside_radius():
    school = School.objects.create(name="Riverside Primary")
    geofence = Geofence.objects.create(
        school=school,
        name="Main Campus",
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=50,
    )

    assert geofence.contains_point(0.001, 0.0) is False


@pytest.mark.django_db
def test_geofence_distance_to_returns_meters_from_center():
    school = School.objects.create(name="Riverside Primary")
    geofence = Geofence.objects.create(
        school=school,
        name="Main Campus",
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=50,
    )

    assert geofence.distance_to(0.001, 0.0) == pytest.approx(111.19, abs=1.0)
