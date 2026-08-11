from django.contrib import admin

from schools.models import Geofence, School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")


@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "radius_m")
    list_filter = ("school",)
