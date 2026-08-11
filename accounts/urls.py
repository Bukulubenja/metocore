from django.urls import path

from accounts.views import accept_invitation

urlpatterns = [
    path("invitations/<str:token>/accept/", accept_invitation, name="accept-invitation"),
]
