from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("role", "school")}),)
    list_display = ("username", "email", "role", "school", "is_staff")
    list_filter = UserAdmin.list_filter + ("role",)
