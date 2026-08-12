from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import CheckIn
from attendance.serializers import (
    CheckInRequestSerializer,
    CheckInResponseSerializer,
    CheckOutRequestSerializer,
)
from attendance.status import determine_checkin_status
from schools.models import Geofence


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
