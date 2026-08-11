"""
URL configuration for metocore project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from accounts.views import (
    manage_teachers,
    teacher_invitation_resend,
    teacher_invitation_revoke,
    teacher_remove,
)
from attendance.views import check_in_page, dashboard, home_redirect
from schools.views import geofence_edit, manage_geofences

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('home/', home_redirect, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('check-in/', check_in_page, name='check-in-page'),
    path('teachers/', manage_teachers, name='teacher-list'),
    path(
        'teachers/<int:invitation_id>/revoke/',
        teacher_invitation_revoke,
        name='teacher-invitation-revoke',
    ),
    path(
        'teachers/<int:invitation_id>/resend/',
        teacher_invitation_resend,
        name='teacher-invitation-resend',
    ),
    path('teachers/<int:user_id>/remove/', teacher_remove, name='teacher-remove'),
    path('geofences/', manage_geofences, name='geofence-list'),
    path('geofences/<int:geofence_id>/edit/', geofence_edit, name='geofence-edit'),
    path('api/', include('attendance.urls')),
    path('platform/', include('schools.urls')),
    path('', include('accounts.urls')),
]
