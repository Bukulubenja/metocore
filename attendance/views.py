import calendar
import csv
import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from attendance.models import CheckIn
from attendance.serializers import (
    CheckInRequestSerializer,
    CheckInResponseSerializer,
    CheckOutRequestSerializer,
)
from attendance.status import determine_checkin_status
from schools.models import Geofence, Term


@login_required
def dashboard(request):
    if not request.user.is_school_admin():
        raise PermissionDenied("Only school admins can view the dashboard.")

    today = timezone.localdate()
    check_ins = CheckIn.objects.filter(
        teacher__school=request.user.school,
        checked_in_at__date=today,
    ).select_related("teacher", "geofence")

    return render(
        request, "attendance/dashboard.html", {"check_ins": check_ins, "today": today}
    )


@login_required
def check_in_page(request):
    if not request.user.is_teacher():
        raise PermissionDenied("Only teachers can check in.")

    today_check_in = (
        CheckIn.objects.filter(
            teacher=request.user,
            status=CheckIn.Status.CONFIRMED,
            checked_in_at__date=timezone.localdate(),
        )
        .order_by("-checked_in_at")
        .first()
    )

    return render(
        request, "attendance/check_in.html", {"today_check_in": today_check_in}
    )


@login_required
def teacher_calendar(request, teacher_id):
    if not request.user.is_school_admin():
        raise PermissionDenied("Only school admins can view attendance calendars.")

    teacher = get_object_or_404(
        User, pk=teacher_id, school=request.user.school, role=User.Role.TEACHER
    )

    today = timezone.localdate()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    first_of_month = datetime.date(year, month, 1)
    last_of_month = datetime.date(year, month, calendar.monthrange(year, month)[1])

    check_ins = CheckIn.objects.filter(
        teacher=teacher,
        checked_in_at__date__gte=first_of_month,
        checked_in_at__date__lte=last_of_month,
    )

    status_priority = {
        CheckIn.Status.CONFIRMED: 3,
        CheckIn.Status.NEEDS_REVIEW: 2,
        CheckIn.Status.OUT_OF_RANGE: 1,
    }
    day_status = {}
    for check_in in check_ins:
        day = timezone.localtime(check_in.checked_in_at).day
        current = day_status.get(day)
        if current is None or status_priority[check_in.status] > status_priority[current]:
            day_status[day] = check_in.status

    month_weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
    weeks = [
        [{"day": day, "status": day_status.get(day)} if day else None for day in week]
        for week in month_weeks
    ]

    prev_last_day = first_of_month - datetime.timedelta(days=1)
    next_first_day = (last_of_month + datetime.timedelta(days=1))

    return render(
        request,
        "attendance/teacher_calendar.html",
        {
            "teacher": teacher,
            "weeks": weeks,
            "month_label": first_of_month.strftime("%B %Y"),
            "prev_year": prev_last_day.year,
            "prev_month": prev_last_day.month,
            "next_year": next_first_day.year,
            "next_month": next_first_day.month,
        },
    )


def _resolve_report_period(request):
    term_id = request.GET.get("term_id", "").strip()
    if term_id:
        term = Term.objects.filter(pk=term_id, school=request.user.school).first()
        if term is None:
            return None, None, "—", "—", ["Selected term not found."]
        return term.start_date, term.end_date, term.academic_year, term.name, []

    errors = []
    start_date = None
    end_date = None
    try:
        start_date = datetime.date.fromisoformat(request.GET.get("start_date", ""))
    except ValueError:
        errors.append("Start date must be a valid date.")
    try:
        end_date = datetime.date.fromisoformat(request.GET.get("end_date", ""))
    except ValueError:
        errors.append("End date must be a valid date.")
    if start_date and end_date and end_date < start_date:
        errors.append("End date must be on or after the start date.")

    return start_date, end_date, "—", "—", errors


def _build_report_rows(school, start_date, end_date, academic_year, term_name):
    teachers = User.objects.filter(school=school, role=User.Role.TEACHER)
    rows = []
    for teacher in teachers:
        count = CheckIn.objects.filter(
            teacher=teacher,
            status=CheckIn.Status.CONFIRMED,
            checked_in_at__date__gte=start_date,
            checked_in_at__date__lte=end_date,
        ).count()
        rows.append(
            {
                "teacher": teacher,
                "count": count,
                "academic_year": academic_year,
                "term": term_name,
            }
        )
    return rows


@login_required
def attendance_report(request):
    if not request.user.is_school_admin():
        raise PermissionDenied("Only school admins can view attendance reports.")

    school = request.user.school
    terms = school.terms.all()

    rows = None
    errors = []
    if request.GET:
        start_date, end_date, academic_year, term_name, errors = _resolve_report_period(
            request
        )
        if not errors:
            rows = _build_report_rows(school, start_date, end_date, academic_year, term_name)

    return render(
        request,
        "attendance/attendance_report.html",
        {
            "terms": terms,
            "rows": rows,
            "errors": errors,
            "query_string": request.GET.urlencode(),
        },
    )


@login_required
def attendance_report_export(request):
    if not request.user.is_school_admin():
        raise PermissionDenied("Only school admins can export attendance reports.")

    school = request.user.school
    start_date, end_date, academic_year, term_name, errors = _resolve_report_period(request)
    if errors:
        return HttpResponseBadRequest(" ".join(errors))

    rows = _build_report_rows(school, start_date, end_date, academic_year, term_name)

    response = HttpResponse(content_type="text/csv")
    filename = f"attendance_report_{school.name}_{start_date}_{end_date}.csv".replace(" ", "_")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        ["Teacher Name", "Title", "School", "Academic Year", "Term", "Attendance Count"]
    )
    for row in rows:
        teacher = row["teacher"]
        name = teacher.get_full_name() or teacher.username
        writer.writerow(
            [name, teacher.title, school.name, row["academic_year"], row["term"], row["count"]]
        )

    return response


@login_required
def home_redirect(request):
    if request.user.is_superuser:
        return redirect("platform-school-list")
    if request.user.is_school_admin():
        return redirect("dashboard")
    return redirect("check-in-page")


class CheckInCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not request.user.is_teacher():
            return Response(
                {"detail": "Only teachers can submit check-ins."},
                status=status.HTTP_403_FORBIDDEN,
            )

        request_serializer = CheckInRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        school = request.user.school
        if school is None:
            return Response(
                {"detail": "You are not assigned to a school. Contact your administrator."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        geofences = list(Geofence.objects.filter(school=school))
        if not geofences:
            return Response(
                {
                    "detail": (
                        "No check-in zones are configured for your school yet. "
                        "Contact your administrator."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        nearest_geofence = min(
            geofences,
            key=lambda g: g.distance_to(data["latitude"], data["longitude"]),
        )

        distance_m = nearest_geofence.distance_to(data["latitude"], data["longitude"])
        projected_status, _ = determine_checkin_status(
            distance_m, data["gps_accuracy_m"], nearest_geofence.radius_m
        )

        if projected_status == CheckIn.Status.CONFIRMED:
            already_confirmed_today = CheckIn.objects.filter(
                teacher=request.user,
                status=CheckIn.Status.CONFIRMED,
                checked_in_at__date=timezone.localdate(),
            ).exists()
            if already_confirmed_today:
                return Response(
                    {"detail": "You've already checked in today."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        check_in = CheckIn.create_from_location(
            teacher=request.user,
            geofence=nearest_geofence,
            latitude=data["latitude"],
            longitude=data["longitude"],
            gps_accuracy_m=data["gps_accuracy_m"],
        )

        return Response(
            CheckInResponseSerializer(check_in).data, status=status.HTTP_201_CREATED
        )


class CheckOutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not request.user.is_teacher():
            return Response(
                {"detail": "Only teachers can check out."},
                status=status.HTTP_403_FORBIDDEN,
            )

        request_serializer = CheckOutRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        today_check_in = (
            CheckIn.objects.filter(
                teacher=request.user,
                status=CheckIn.Status.CONFIRMED,
                checked_in_at__date=timezone.localdate(),
                checked_out_at__isnull=True,
            )
            .order_by("-checked_in_at")
            .first()
        )
        if today_check_in is None:
            return Response(
                {"detail": "No confirmed check-in found for today to check out from."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today_check_in.record_checkout(
            latitude=data["latitude"],
            longitude=data["longitude"],
            gps_accuracy_m=data["gps_accuracy_m"],
        )

        return Response(
            CheckInResponseSerializer(today_check_in).data, status=status.HTTP_200_OK
        )
