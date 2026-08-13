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
from django.views.generic.base import RedirectView

from accounts.views import (
    manage_teachers,
    teacher_invitation_resend,
    teacher_invitation_revoke,
    teacher_remove,
    teacher_update_title,
)
from announcements.views import announcement_delete, announcement_list
from attendance.views import (
    attendance_report,
    attendance_report_export,
    check_in_page,
    dashboard,
    home_redirect,
    teacher_calendar,
)
from events.views import event_delete, event_list
from schools.views import geofence_edit, manage_geofences, manage_terms, term_edit
from timetable.views import (
    class_delete,
    class_edit,
    generate_timetable_view,
    manage_classes,
    manage_lesson_requirements,
    manage_periods,
    manage_subjects,
    manage_teacher_availability,
    my_timetable,
    period_delete,
    period_edit,
    requirement_delete,
    requirement_edit,
    subject_delete,
    subject_edit,
    timetable_entry_edit,
    timetable_view,
)

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='home', permanent=False)),
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
    path('teachers/<int:user_id>/title/', teacher_update_title, name='teacher-update-title'),
    path('teachers/<int:teacher_id>/calendar/', teacher_calendar, name='teacher-calendar'),
    path('geofences/', manage_geofences, name='geofence-list'),
    path('geofences/<int:geofence_id>/edit/', geofence_edit, name='geofence-edit'),
    path('terms/', manage_terms, name='term-list'),
    path('terms/<int:term_id>/edit/', term_edit, name='term-edit'),
    path('announcements/', announcement_list, name='announcement-list'),
    path(
        'announcements/<int:announcement_id>/delete/',
        announcement_delete,
        name='announcement-delete',
    ),
    path('events/', event_list, name='event-list'),
    path('events/<int:event_id>/delete/', event_delete, name='event-delete'),
    path('reports/attendance/', attendance_report, name='attendance-report'),
    path(
        'reports/attendance/export/', attendance_report_export, name='attendance-report-export'
    ),
    path('timetable/periods/', manage_periods, name='timetable-period-list'),
    path('timetable/periods/<int:period_id>/edit/', period_edit, name='timetable-period-edit'),
    path(
        'timetable/periods/<int:period_id>/delete/', period_delete, name='timetable-period-delete'
    ),
    path('timetable/subjects/', manage_subjects, name='timetable-subject-list'),
    path(
        'timetable/subjects/<int:subject_id>/edit/', subject_edit, name='timetable-subject-edit'
    ),
    path(
        'timetable/subjects/<int:subject_id>/delete/',
        subject_delete,
        name='timetable-subject-delete',
    ),
    path('timetable/classes/', manage_classes, name='timetable-class-list'),
    path('timetable/classes/<int:class_id>/edit/', class_edit, name='timetable-class-edit'),
    path(
        'timetable/classes/<int:class_id>/delete/', class_delete, name='timetable-class-delete'
    ),
    path(
        'timetable/availability/',
        manage_teacher_availability,
        name='timetable-availability',
    ),
    path(
        'timetable/requirements/',
        manage_lesson_requirements,
        name='timetable-requirement-list',
    ),
    path(
        'timetable/requirements/<int:requirement_id>/edit/',
        requirement_edit,
        name='timetable-requirement-edit',
    ),
    path(
        'timetable/requirements/<int:requirement_id>/delete/',
        requirement_delete,
        name='timetable-requirement-delete',
    ),
    path('timetable/generate/', generate_timetable_view, name='timetable-generate'),
    path('timetable/', timetable_view, name='timetable-view'),
    path(
        'timetable/entries/<int:entry_id>/edit/',
        timetable_entry_edit,
        name='timetable-entry-edit',
    ),
    path('my-timetable/', my_timetable, name='my-timetable'),
    path('api/', include('attendance.urls')),
    path('platform/', include('schools.urls')),
    path('', include('accounts.urls')),
]
