import datetime
import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        TEACHER = "TEACHER", "Teacher"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.TEACHER)
    school = models.ForeignKey(
        "schools.School",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff",
    )

    def is_teacher(self) -> bool:
        return self.role == self.Role.TEACHER

    def is_school_admin(self) -> bool:
        return self.role == self.Role.ADMIN


class SchoolAdminInvitation(models.Model):
    DEFAULT_VALIDITY = datetime.timedelta(days=7)

    email = models.EmailField()
    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="admin_invitations"
    )
    token = models.CharField(max_length=64, unique=True)
    role = models.CharField(max_length=10, choices=User.Role.choices, default=User.Role.ADMIN)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Invite for {self.email} to {self.school.name}"

    @classmethod
    def create_for(
        cls, *, email: str, school, invited_by, role: str = User.Role.ADMIN
    ) -> "SchoolAdminInvitation":
        return cls.objects.create(
            email=email,
            school=school,
            invited_by=invited_by,
            role=role,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + cls.DEFAULT_VALIDITY,
        )

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def is_valid(self) -> bool:
        return self.accepted_at is None and self.revoked_at is None and not self.is_expired

    def revoke(self) -> None:
        if self.accepted_at is not None:
            raise ValueError("Cannot revoke an invitation that has already been accepted.")
        if self.revoked_at is not None:
            raise ValueError("This invitation has already been revoked.")

        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    def resend(self) -> None:
        if self.accepted_at is not None:
            raise ValueError("Cannot resend an invitation that has already been accepted.")
        if self.revoked_at is not None:
            raise ValueError("Cannot resend a revoked invitation.")

        self.expires_at = timezone.now() + self.DEFAULT_VALIDITY
        self.save(update_fields=["expires_at"])

    def accept(self, *, username: str, password: str) -> User:
        if not self.is_valid():
            raise ValueError("This invitation is no longer valid.")

        user = User.objects.create_user(
            username=username,
            email=self.email,
            password=password,
            role=self.role,
            school=self.school,
        )
        self.accepted_at = timezone.now()
        self.save(update_fields=["accepted_at"])
        return user
