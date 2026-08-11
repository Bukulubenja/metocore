from django.db import models

from schools.geo import distance_meters


class School(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Geofence(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="geofences")
    name = models.CharField(max_length=255)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_m = models.PositiveIntegerField()

    def __str__(self) -> str:
        return f"{self.school.name} — {self.name}"

    def distance_to(self, latitude: float, longitude: float) -> float:
        return distance_meters(
            float(self.center_latitude), float(self.center_longitude), latitude, longitude
        )

    def contains_point(self, latitude: float, longitude: float) -> bool:
        return self.distance_to(latitude, longitude) <= self.radius_m
