from django.conf import settings
from django.db import models


class Announcement(models.Model):
    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="announcements"
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.school.name} — {self.title}"
