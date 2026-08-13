from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from announcements.models import Announcement


def _require_school_staff(request) -> None:
    if request.user.school is None:
        raise PermissionDenied("You must belong to a school to view announcements.")


def _require_school_admin(request) -> None:
    if not request.user.is_school_admin():
        raise PermissionDenied("Only school admins can manage announcements.")


@login_required
def announcement_list(request):
    _require_school_staff(request)
    school = request.user.school

    if request.method == "POST":
        _require_school_admin(request)
        title = request.POST.get("title", "").strip()
        body = request.POST.get("body", "").strip()
        if title and body:
            Announcement.objects.create(
                school=school, title=title, body=body, created_by=request.user
            )
            messages.success(request, f"Posted announcement '{title}'.")
        else:
            messages.error(request, "Title and body are required.")
        return redirect("announcement-list")

    announcements = school.announcements.all()
    return render(
        request, "announcements/announcement_list.html", {"announcements": announcements}
    )


@login_required
def announcement_delete(request, announcement_id):
    _require_school_admin(request)
    announcement = get_object_or_404(
        Announcement, pk=announcement_id, school=request.user.school
    )

    if request.method == "POST":
        announcement.delete()
        messages.success(request, "Announcement deleted.")

    return redirect("announcement-list")
