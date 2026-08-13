from django.conf import settings
from django.db import models


class Event(models.Model):
    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="events"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.school.name} — {self.title} ({self.date})"
