import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from events.models import Event


def _require_school_staff(request) -> None:
    if request.user.school is None:
        raise PermissionDenied("You must belong to a school to view events.")


def _require_school_admin(request) -> None:
    if not request.user.is_school_admin():
        raise PermissionDenied("Only school admins can manage events.")


def _parse_event_fields(post):
    errors = []

    title = post.get("title", "").strip()
    if not title:
        errors.append("Title is required.")

    date = None
    try:
        date = datetime.date.fromisoformat(post.get("date", ""))
    except ValueError:
        errors.append("Date must be a valid date.")

    description = post.get("description", "").strip()
    location = post.get("location", "").strip()

    return title, description, date, location, errors


@login_required
def event_list(request):
    _require_school_staff(request)
    school = request.user.school

    if request.method == "POST":
        _require_school_admin(request)
        title, description, date, location, errors = _parse_event_fields(request.POST)
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            Event.objects.create(
                school=school,
                title=title,
                description=description,
                date=date,
                location=location,
                created_by=request.user,
            )
            messages.success(request, f"Added event '{title}'.")
        return redirect("event-list")

    today = timezone.localdate()
    events = school.events.all()
    upcoming_events = events.filter(date__gte=today)
    past_events = events.filter(date__lt=today).order_by("-date")
    return render(
        request,
        "events/event_list.html",
        {"upcoming_events": upcoming_events, "past_events": past_events},
    )


@login_required
def event_delete(request, event_id):
    _require_school_admin(request)
    event = get_object_or_404(Event, pk=event_id, school=request.user.school)

    if request.method == "POST":
        event.delete()
        messages.success(request, "Event deleted.")

    return redirect("event-list")
