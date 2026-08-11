import pytest
from django.core import mail

from accounts.models import SchoolAdminInvitation, User
from schools.models import School


@pytest.fixture
def platform_admin():
    return User.objects.create_superuser(username="platform", password="x", email="p@example.com")


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.fixture
def school_admin(school):
    return User.objects.create_user(
        username="principal", password="x", role=User.Role.ADMIN, school=school
    )


@pytest.mark.django_db
def test_school_list_requires_login(client):
    response = client.get("/platform/schools/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_school_list_forbidden_for_non_superuser(client, school_admin):
    client.force_login(school_admin)

    response = client.get("/platform/schools/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_school_list_shows_existing_schools(client, platform_admin, school):
    client.force_login(platform_admin)

    response = client.get("/platform/schools/")

    assert response.status_code == 200
    assert b"Riverside Primary" in response.content


@pytest.mark.django_db
def test_creating_school_via_post(client, platform_admin):
    client.force_login(platform_admin)

    response = client.post("/platform/schools/", {"name": "Hillcrest Academy"})

    assert response.status_code == 302
    assert School.objects.filter(name="Hillcrest Academy").exists()


@pytest.mark.django_db
def test_creating_school_with_blank_name_does_not_create(client, platform_admin):
    client.force_login(platform_admin)

    client.post("/platform/schools/", {"name": ""})

    assert School.objects.count() == 0


@pytest.mark.django_db
def test_school_detail_requires_superuser(client, school_admin, school):
    client.force_login(school_admin)

    response = client.get(f"/platform/schools/{school.id}/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_school_detail_shows_existing_admins(client, platform_admin, school, school_admin):
    client.force_login(platform_admin)

    response = client.get(f"/platform/schools/{school.id}/")

    assert response.status_code == 200
    assert b"principal" in response.content


@pytest.mark.django_db
def test_inviting_admin_creates_invitation_and_sends_email(client, platform_admin, school):
    client.force_login(platform_admin)

    response = client.post(
        f"/platform/schools/{school.id}/", {"email": "new.admin@example.com"}
    )

    assert response.status_code == 302
    invitation = SchoolAdminInvitation.objects.get(email="new.admin@example.com", school=school)
    assert invitation.invited_by == platform_admin
    assert len(mail.outbox) == 1
    assert "new.admin@example.com" in mail.outbox[0].to
    assert invitation.token in mail.outbox[0].body


@pytest.mark.django_db
def test_inviting_admin_with_blank_email_does_not_create_invitation(
    client, platform_admin, school
):
    client.force_login(platform_admin)

    client.post(f"/platform/schools/{school.id}/", {"email": ""})

    assert SchoolAdminInvitation.objects.count() == 0
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_school_detail_shows_pending_invitation(client, platform_admin, school):
    SchoolAdminInvitation.create_for(
        email="pending@example.com", school=school, invited_by=platform_admin
    )
    client.force_login(platform_admin)

    response = client.get(f"/platform/schools/{school.id}/")

    assert b"pending@example.com" in response.content


# --- revoke invitation -------------------------------------------------------

@pytest.mark.django_db
def test_revoke_invitation_marks_it_revoked(client, platform_admin, school):
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com", school=school, invited_by=platform_admin
    )
    client.force_login(platform_admin)

    response = client.post(
        f"/platform/schools/{school.id}/invitations/{invitation.id}/revoke/"
    )

    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.revoked_at is not None


@pytest.mark.django_db
def test_revoke_invitation_requires_superuser(client, school_admin, school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com", school=school, invited_by=platform_admin
    )
    client.force_login(school_admin)

    response = client.post(
        f"/platform/schools/{school.id}/invitations/{invitation.id}/revoke/"
    )

    assert response.status_code == 403
    invitation.refresh_from_db()
    assert invitation.revoked_at is None


@pytest.mark.django_db
def test_revoke_invitation_404_for_wrong_school(client, platform_admin, school):
    other_school = School.objects.create(name="Hillcrest Academy")
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com", school=other_school, invited_by=platform_admin
    )
    client.force_login(platform_admin)

    response = client.post(
        f"/platform/schools/{school.id}/invitations/{invitation.id}/revoke/"
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_revoke_already_accepted_invitation_shows_error(client, platform_admin, school):
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com", school=school, invited_by=platform_admin
    )
    invitation.accept(username="newadmin", password="a-strong-passw0rd")
    client.force_login(platform_admin)

    response = client.post(
        f"/platform/schools/{school.id}/invitations/{invitation.id}/revoke/",
        follow=True,
    )

    assert response.status_code == 200
    assert b"already been accepted" in response.content


# --- resend invitation --------------------------------------------------------

@pytest.mark.django_db
def test_resend_invitation_sends_email_and_extends_expiry(client, platform_admin, school):
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com", school=school, invited_by=platform_admin
    )
    original_expiry = invitation.expires_at
    client.force_login(platform_admin)

    response = client.post(
        f"/platform/schools/{school.id}/invitations/{invitation.id}/resend/"
    )

    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.expires_at > original_expiry
    assert len(mail.outbox) == 1
    assert "pending@example.com" in mail.outbox[0].to


@pytest.mark.django_db
def test_resend_invitation_requires_superuser(client, school_admin, school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com", school=school, invited_by=platform_admin
    )
    client.force_login(school_admin)

    response = client.post(
        f"/platform/schools/{school.id}/invitations/{invitation.id}/resend/"
    )

    assert response.status_code == 403
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_resend_already_accepted_invitation_shows_error(client, platform_admin, school):
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com", school=school, invited_by=platform_admin
    )
    invitation.accept(username="newadmin", password="a-strong-passw0rd")
    client.force_login(platform_admin)

    response = client.post(
        f"/platform/schools/{school.id}/invitations/{invitation.id}/resend/",
        follow=True,
    )

    assert response.status_code == 200
    assert len(mail.outbox) == 0


# --- remove admin --------------------------------------------------------------

@pytest.mark.django_db
def test_remove_admin_deactivates_user(client, platform_admin, school, school_admin):
    client.force_login(platform_admin)

    response = client.post(
        f"/platform/schools/{school.id}/admins/{school_admin.id}/remove/"
    )

    assert response.status_code == 302
    school_admin.refresh_from_db()
    assert school_admin.is_active is False


@pytest.mark.django_db
def test_remove_admin_requires_superuser(client, school_admin, school):
    other_admin = User.objects.create_user(
        username="otheradmin", password="x", role=User.Role.ADMIN, school=school
    )
    client.force_login(school_admin)

    response = client.post(
        f"/platform/schools/{school.id}/admins/{other_admin.id}/remove/"
    )

    assert response.status_code == 403
    other_admin.refresh_from_db()
    assert other_admin.is_active is True


@pytest.mark.django_db
def test_remove_admin_404_when_user_not_admin_of_that_school(client, platform_admin, school):
    other_school = School.objects.create(name="Hillcrest Academy")
    unrelated_admin = User.objects.create_user(
        username="unrelated", password="x", role=User.Role.ADMIN, school=other_school
    )
    client.force_login(platform_admin)

    response = client.post(
        f"/platform/schools/{school.id}/admins/{unrelated_admin.id}/remove/"
    )

    assert response.status_code == 404
    unrelated_admin.refresh_from_db()
    assert unrelated_admin.is_active is True
