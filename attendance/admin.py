from django.contrib import admin

from attendance.models import CheckIn


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ("teacher", "checked_in_at", "status", "distance_m", "gps_accuracy_m")
    list_filter = ("status", "geofence__school")
    readonly_fields = [f.name for f in CheckIn._meta.fields]
