import pytest
from django.core import mail

from accounts.models import SchoolAdminInvitation, User
from schools.models import School


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.fixture
def other_school():
    return School.objects.create(name="Hillcrest Academy")


@pytest.fixture
def school_admin(school):
    return User.objects.create_user(
        username="principal", password="x", role=User.Role.ADMIN, school=school
    )


@pytest.fixture
def teacher(school):
    return User.objects.create_user(
        username="jdoe", password="x", role=User.Role.TEACHER, school=school
    )


@pytest.mark.django_db
def test_manage_teachers_requires_login(client):
    response = client.get("/teachers/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_manage_teachers_forbidden_for_teacher(client, teacher):
    client.force_login(teacher)

    response = client.get("/teachers/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_manage_teachers_shows_only_own_schools_teachers(
    client, school_admin, teacher, other_school
):
    other_teacher = User.objects.create_user(
        username="msmith", password="x", role=User.Role.TEACHER, school=other_school
    )
    client.force_login(school_admin)

    response = client.get("/teachers/")

    assert response.status_code == 200
    assert b"jdoe" in response.content
    assert b"msmith" not in response.content


@pytest.mark.django_db
def test_inviting_teacher_creates_teacher_role_invitation_and_sends_email(
    client, school_admin, school
):
    client.force_login(school_admin)

    response = client.post("/teachers/", {"email": "new.teacher@example.com"})

    assert response.status_code == 302
    invitation = SchoolAdminInvitation.objects.get(email="new.teacher@example.com")
    assert invitation.school == school
    assert invitation.role == User.Role.TEACHER
    assert invitation.invited_by == school_admin
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_inviting_teacher_with_blank_email_does_not_create_invitation(
    client, school_admin
):
    client.force_login(school_admin)

    client.post("/teachers/", {"email": ""})

    assert SchoolAdminInvitation.objects.count() == 0


@pytest.mark.django_db
def test_revoke_teacher_invitation(client, school_admin, school):
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com",
        school=school,
        invited_by=school_admin,
        role=User.Role.TEACHER,
    )
    client.force_login(school_admin)

    response = client.post(f"/teachers/{invitation.id}/revoke/")

    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.revoked_at is not None


@pytest.mark.django_db
def test_revoke_teacher_invitation_404_for_other_school(
    client, school_admin, other_school
):
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com",
        school=other_school,
        invited_by=school_admin,
        role=User.Role.TEACHER,
    )
    client.force_login(school_admin)

    response = client.post(f"/teachers/{invitation.id}/revoke/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_resend_teacher_invitation(client, school_admin, school):
    invitation = SchoolAdminInvitation.create_for(
        email="pending@example.com",
        school=school,
        invited_by=school_admin,
        role=User.Role.TEACHER,
    )
    original_expiry = invitation.expires_at
    client.force_login(school_admin)

    response = client.post(f"/teachers/{invitation.id}/resend/")

    assert response.status_code == 302
    invitation.refresh_from_db()
    assert invitation.expires_at > original_expiry
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_remove_teacher_deactivates_user(client, school_admin, teacher):
    client.force_login(school_admin)

    response = client.post(f"/teachers/{teacher.id}/remove/")

    assert response.status_code == 302
    teacher.refresh_from_db()
    assert teacher.is_active is False


@pytest.mark.django_db
def test_remove_teacher_404_for_other_school(client, school_admin, other_school):
    other_teacher = User.objects.create_user(
        username="msmith", password="x", role=User.Role.TEACHER, school=other_school
    )
    client.force_login(school_admin)

    response = client.post(f"/teachers/{other_teacher.id}/remove/")

    assert response.status_code == 404
    other_teacher.refresh_from_db()
    assert other_teacher.is_active is True
