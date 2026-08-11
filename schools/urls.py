from django.urls import path

from schools import views

urlpatterns = [
    path("schools/", views.school_list, name="platform-school-list"),
    path("schools/<int:school_id>/", views.school_detail, name="platform-school-detail"),
    path(
        "schools/<int:school_id>/invitations/<int:invitation_id>/revoke/",
        views.invitation_revoke,
        name="platform-invitation-revoke",
    ),
    path(
        "schools/<int:school_id>/invitations/<int:invitation_id>/resend/",
        views.invitation_resend,
        name="platform-invitation-resend",
    ),
    path(
        "schools/<int:school_id>/admins/<int:user_id>/remove/",
        views.admin_remove,
        name="platform-admin-remove",
    ),
]
