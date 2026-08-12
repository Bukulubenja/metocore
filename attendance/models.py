from django.conf import settings
from django.db import models
from django.utils import timezone

from attendance.status import determine_checkin_status
from schools.models import Geofence


class CheckIn(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        OUT_OF_RANGE = "OUT_OF_RANGE", "Out of range"
        NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="check_ins"
    )
    geofence = models.ForeignKey(Geofence, on_delete=models.CASCADE, related_name="check_ins")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    gps_accuracy_m = models.PositiveIntegerField()
    distance_m = models.FloatField()
    status = models.CharField(max_length=20, choices=Status.choices)
    reason = models.TextField()
    checked_in_at = models.DateTimeField(default=timezone.now)

    checked_out_at = models.DateTimeField(null=True, blank=True)
    checkout_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    checkout_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    checkout_gps_accuracy_m = models.PositiveIntegerField(null=True, blank=True)
    checkout_distance_m = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["-checked_in_at"]

    def __str__(self) -> str:
        return f"{self.teacher} @ {self.checked_in_at:%Y-%m-%d %H:%M} — {self.status}"

    @classmethod
    def create_from_location(
        cls,
        teacher,
        geofence: Geofence,
        latitude: float,
        longitude: float,
        gps_accuracy_m: int,
    ) -> "CheckIn":
        distance_m = geofence.distance_to(latitude, longitude)
        status, reason = determine_checkin_status(distance_m, gps_accuracy_m, geofence.radius_m)

        return cls.objects.create(
            teacher=teacher,
            geofence=geofence,
            latitude=latitude,
            longitude=longitude,
            gps_accuracy_m=gps_accuracy_m,
            distance_m=distance_m,
            status=status,
            reason=reason,
        )

    def record_checkout(self, latitude: float, longitude: float, gps_accuracy_m: int) -> None:
        self.checkout_latitude = latitude
        self.checkout_longitude = longitude
        self.checkout_gps_accuracy_m = gps_accuracy_m
        self.checkout_distance_m = self.geofence.distance_to(latitude, longitude)
        self.checked_out_at = timezone.now()
        self.save(
            update_fields=[
                "checkout_latitude",
                "checkout_longitude",
                "checkout_gps_accuracy_m",
                "checkout_distance_m",
                "checked_out_at",
            ]
        )
