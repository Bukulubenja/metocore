from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from accounts.models import SchoolAdminInvitation


def send_invitation_email(invitation: SchoolAdminInvitation, request) -> None:
    accept_url = request.build_absolute_uri(
        reverse("accept-invitation", args=[invitation.token])
    )
    send_mail(
        subject=f"You're invited to manage {invitation.school.name} on Metocore",
        message=(
            f"You've been invited to be an administrator for {invitation.school.name}.\n\n"
            f"Accept your invitation here: {accept_url}\n\n"
            f"This link expires on {invitation.expires_at:%Y-%m-%d}."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
    )
