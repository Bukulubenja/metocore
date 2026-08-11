from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.emails import send_invitation_email
from accounts.models import SchoolAdminInvitation, User


def _require_school_admin(request) -> None:
    if not request.user.is_school_admin():
        raise PermissionDenied("Only school admins can manage teachers.")


def accept_invitation(request, token):
    invitation = get_object_or_404(SchoolAdminInvitation, token=token)

    if not invitation.is_valid():
        return render(
            request, "accounts/invitation_invalid.html", {"invitation": invitation}, status=410
        )

    errors: list[str] = []

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username:
            errors.append("Username is required.")
        elif User.objects.filter(username=username).exists():
            errors.append("That username is already taken.")

        try:
            validate_password(password)
        except DjangoValidationError as exc:
            errors.extend(exc.messages)

        if not errors:
            user = invitation.accept(username=username, password=password)
            login(request, user)
            return redirect("home")

    return render(
        request, "accounts/accept_invitation.html", {"invitation": invitation, "errors": errors}
    )


@login_required
def manage_teachers(request):
    _require_school_admin(request)
    school = request.user.school

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if email:
            invitation = SchoolAdminInvitation.create_for(
                email=email, school=school, invited_by=request.user, role=User.Role.TEACHER
            )
            send_invitation_email(invitation, request)
            messages.success(request, f"Invitation sent to {email}.")
        else:
            messages.error(request, "Email is required.")
        return redirect("teacher-list")

    teachers = User.objects.filter(school=school, role=User.Role.TEACHER)
    invitations = SchoolAdminInvitation.objects.filter(
        school=school, role=User.Role.TEACHER
    ).order_by("-created_at")
    return render(
        request,
        "accounts/manage_teachers.html",
        {"teachers": teachers, "invitations": invitations},
    )


@login_required
def teacher_invitation_revoke(request, invitation_id):
    _require_school_admin(request)
    invitation = get_object_or_404(
        SchoolAdminInvitation,
        pk=invitation_id,
        school=request.user.school,
        role=User.Role.TEACHER,
    )

    try:
        invitation.revoke()
        messages.success(request, f"Invitation to {invitation.email} revoked.")
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect("teacher-list")


@login_required
def teacher_invitation_resend(request, invitation_id):
    _require_school_admin(request)
    invitation = get_object_or_404(
        SchoolAdminInvitation,
        pk=invitation_id,
        school=request.user.school,
        role=User.Role.TEACHER,
    )

    try:
        invitation.resend()
        send_invitation_email(invitation, request)
        messages.success(request, f"Invitation resent to {invitation.email}.")
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect("teacher-list")


@login_required
def teacher_remove(request, user_id):
    _require_school_admin(request)
    teacher = get_object_or_404(
        User, pk=user_id, school=request.user.school, role=User.Role.TEACHER
    )

    teacher.is_active = False
    teacher.save(update_fields=["is_active"])
    messages.success(request, f"Removed {teacher.username}'s access.")

    return redirect("teacher-list")
