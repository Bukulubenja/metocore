from django.urls import path

from attendance.views import CheckInCreateView

urlpatterns = [
    path("check-ins/", CheckInCreateView.as_view(), name="check-in-create"),
]
