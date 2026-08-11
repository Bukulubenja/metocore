from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from accounts.emails import send_invitation_email
from accounts.models import SchoolAdminInvitation, User
from schools.models import Geofence, School


def _require_platform_admin(request) -> None:
    if not request.user.is_superuser:
        raise PermissionDenied("Only platform administrators can manage schools.")


def _require_school_admin(request) -> None:
    if not request.user.is_school_admin():
        raise PermissionDenied("Only school admins can manage geofences.")


def _parse_geofence_fields(post):
    errors = []

    name = post.get("name", "").strip()
    if not name:
        errors.append("Name is required.")

    latitude = None
    try:
        latitude = float(post.get("center_latitude", ""))
        if not (-90 <= latitude <= 90):
            errors.append("Latitude must be between -90 and 90.")
    except ValueError:
        errors.append("Latitude must be a number.")

    longitude = None
    try:
        longitude = float(post.get("center_longitude", ""))
        if not (-180 <= longitude <= 180):
            errors.append("Longitude must be between -180 and 180.")
    except ValueError:
        errors.append("Longitude must be a number.")

    radius_m = None
    try:
        radius_m = int(post.get("radius_m", ""))
        if radius_m <= 0:
            errors.append("Radius must be a positive number of meters.")
    except ValueError:
        errors.append("Radius must be a whole number of meters.")

    return name, latitude, longitude, radius_m, errors


@login_required
def school_list(request):
    _require_platform_admin(request)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            School.objects.create(name=name)
            messages.success(request, f"Created school '{name}'.")
        else:
            messages.error(request, "School name is required.")
        return redirect("platform-school-list")

    schools = School.objects.order_by("name")
    return render(request, "schools/school_list.html", {"schools": schools})


@login_required
def school_detail(request, school_id):
    _require_platform_admin(request)
    school = get_object_or_404(School, pk=school_id)

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if email:
            invitation = SchoolAdminInvitation.create_for(
                email=email, school=school, invited_by=request.user
            )
            send_invitation_email(invitation, request)
            messages.success(request, f"Invitation sent to {email}.")
        else:
            messages.error(request, "Email is required.")
        return redirect("platform-school-detail", school_id=school.id)

    admins = school.staff.filter(role=User.Role.ADMIN)
    invitations = school.admin_invitations.order_by("-created_at")
    return render(
        request,
        "schools/school_detail.html",
        {"school": school, "admins": admins, "invitations": invitations},
    )


@login_required
def invitation_revoke(request, school_id, invitation_id):
    _require_platform_admin(request)
    invitation = get_object_or_404(
        SchoolAdminInvitation, pk=invitation_id, school_id=school_id
    )

    try:
        invitation.revoke()
        messages.success(request, f"Invitation to {invitation.email} revoked.")
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect("platform-school-detail", school_id=school_id)


@login_required
def invitation_resend(request, school_id, invitation_id):
    _require_platform_admin(request)
    invitation = get_object_or_404(
        SchoolAdminInvitation, pk=invitation_id, school_id=school_id
    )

    try:
        invitation.resend()
        send_invitation_email(invitation, request)
        messages.success(request, f"Invitation resent to {invitation.email}.")
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect("platform-school-detail", school_id=school_id)


@login_required
def admin_remove(request, school_id, user_id):
    _require_platform_admin(request)
    admin = get_object_or_404(
        User, pk=user_id, school_id=school_id, role=User.Role.ADMIN
    )

    admin.is_active = False
    admin.save(update_fields=["is_active"])
    messages.success(request, f"Removed {admin.username}'s admin access.")

    return redirect("platform-school-detail", school_id=school_id)


@login_required
def manage_geofences(request):
    _require_school_admin(request)
    school = request.user.school

    if request.method == "POST":
        name, latitude, longitude, radius_m, errors = _parse_geofence_fields(request.POST)
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            Geofence.objects.create(
                school=school,
                name=name,
                center_latitude=latitude,
                center_longitude=longitude,
                radius_m=radius_m,
            )
            messages.success(request, f"Created geofence '{name}'.")
        return redirect("geofence-list")

    geofences = school.geofences.order_by("name")
    return render(request, "schools/geofence_list.html", {"geofences": geofences})


@login_required
def geofence_edit(request, geofence_id):
    _require_school_admin(request)
    geofence = get_object_or_404(Geofence, pk=geofence_id, school=request.user.school)

    if request.method == "POST":
        name, latitude, longitude, radius_m, errors = _parse_geofence_fields(request.POST)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("geofence-edit", geofence_id=geofence.id)

        geofence.name = name
        geofence.center_latitude = latitude
        geofence.center_longitude = longitude
        geofence.radius_m = radius_m
        geofence.save()
        messages.success(request, f"Updated geofence '{name}'.")
        return redirect("geofence-list")

    return render(request, "schools/geofence_edit.html", {"geofence": geofence})
