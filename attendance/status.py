LOW_GPS_ACCURACY_THRESHOLD_M = 100


def determine_checkin_status(distance_m: float, gps_accuracy_m: int, radius_m: int) -> tuple[str, str]:
    """Pick a check-in status with a human-readable reason.

    GPS-accuracy takes priority over distance: a location reading too imprecise
    to trust is flagged for human review rather than auto-confirmed or
    auto-rejected, so a bad GPS fix never reads as "suspicious" on its own.
    """
    from attendance.models import CheckIn

    if gps_accuracy_m > LOW_GPS_ACCURACY_THRESHOLD_M:
        return (
            CheckIn.Status.NEEDS_REVIEW,
            f"GPS accuracy was ±{gps_accuracy_m}m, too imprecise to confirm "
            f"location within the {radius_m}m geofence. A staff member will review this check-in.",
        )

    if distance_m <= radius_m:
        return (
            CheckIn.Status.CONFIRMED,
            f"Within the {radius_m}m geofence (measured {distance_m:.0f}m from center).",
        )

    over_by = distance_m - radius_m
    return (
        CheckIn.Status.OUT_OF_RANGE,
        f"Located {distance_m:.0f}m from campus center, {over_by:.0f}m outside the {radius_m}m geofence.",
    )
