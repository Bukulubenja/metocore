import pytest

from accounts.models import User
from attendance.models import CheckIn
from attendance.status import determine_checkin_status
from schools.models import Geofence, School


# --- pure status logic -------------------------------------------------

def test_confirmed_when_within_radius_and_good_gps_accuracy():
    status, reason = determine_checkin_status(distance_m=30, gps_accuracy_m=15, radius_m=100)

    assert status == CheckIn.Status.CONFIRMED
    assert "100m" in reason
    assert "30" in reason


def test_out_of_range_when_outside_radius_with_good_gps_accuracy():
    status, reason = determine_checkin_status(distance_m=250, gps_accuracy_m=15, radius_m=100)

    assert status == CheckIn.Status.OUT_OF_RANGE
    assert "250" in reason
    assert "150" in reason  # how far outside the geofence


def test_needs_review_when_gps_accuracy_too_poor_even_if_within_radius():
    status, reason = determine_checkin_status(distance_m=30, gps_accuracy_m=150, radius_m=100)

    assert status == CheckIn.Status.NEEDS_REVIEW
    assert "150" in reason


def test_needs_review_takes_priority_over_out_of_range():
    status, reason = determine_checkin_status(distance_m=500, gps_accuracy_m=150, radius_m=100)

    assert status == CheckIn.Status.NEEDS_REVIEW


def test_reason_is_never_empty_for_any_status():
    for distance_m, gps_accuracy_m in [(30, 15), (250, 15), (30, 150)]:
        _, reason = determine_checkin_status(distance_m, gps_accuracy_m, radius_m=100)
        assert reason.strip() != ""


# --- model integration ---------------------------------------------------

@pytest.mark.django_db
def test_create_from_location_persists_confirmed_checkin():
    school = School.objects.create(name="Riverside Primary")
    geofence = Geofence.objects.create(
        school=school,
        name="Main Campus",
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=200,
    )
    teacher = User.objects.create_user(username="jdoe", password="x", role=User.Role.TEACHER)

    check_in = CheckIn.create_from_location(
        teacher=teacher,
        geofence=geofence,
        latitude=0.001,
        longitude=0.0,
        gps_accuracy_m=15,
    )

    assert check_in.pk is not None
    assert check_in.status == CheckIn.Status.CONFIRMED
    assert check_in.teacher == teacher
    assert check_in.distance_m == pytest.approx(111.19, abs=1.0)
    assert check_in.reason != ""


@pytest.mark.django_db
def test_create_from_location_flags_low_gps_accuracy_for_review():
    school = School.objects.create(name="Riverside Primary")
    geofence = Geofence.objects.create(
        school=school,
        name="Main Campus",
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=200,
    )
    teacher = User.objects.create_user(username="jdoe", password="x", role=User.Role.TEACHER)

    check_in = CheckIn.create_from_location(
        teacher=teacher,
        geofence=geofence,
        latitude=0.001,
        longitude=0.0,
        gps_accuracy_m=300,
    )

    assert check_in.status == CheckIn.Status.NEEDS_REVIEW
