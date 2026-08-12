from django.urls import path

from attendance.views import CheckInCreateView, CheckOutView

urlpatterns = [
    path("check-ins/", CheckInCreateView.as_view(), name="check-in-create"),
    path("check-outs/", CheckOutView.as_view(), name="check-out-create"),
]
