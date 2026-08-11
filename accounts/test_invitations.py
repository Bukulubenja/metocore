import datetime

import pytest
from django.utils import timezone

from accounts.models import SchoolAdminInvitation, User
from schools.models import School


@pytest.fixture
def school():
    return School.objects.create(name="Riverside Primary")


@pytest.fixture
def platform_admin():
    return User.objects.create_superuser(username="platform", password="x", email="p@example.com")


@pytest.mark.django_db
def test_create_for_generates_token_and_expiry(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )

    assert invitation.token
    assert len(invitation.token) >= 32
    assert invitation.expires_at > timezone.now()
    assert invitation.accepted_at is None


@pytest.mark.django_db
def test_two_invitations_get_different_tokens(school, platform_admin):
    first = SchoolAdminInvitation.create_for(
        email="a@example.com", school=school, invited_by=platform_admin
    )
    second = SchoolAdminInvitation.create_for(
        email="b@example.com", school=school, invited_by=platform_admin
    )

    assert first.token != second.token


@pytest.mark.django_db
def test_is_valid_true_for_fresh_invitation(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )

    assert invitation.is_valid() is True


@pytest.mark.django_db
def test_is_valid_false_when_expired(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.expires_at = timezone.now() - datetime.timedelta(days=1)
    invitation.save(update_fields=["expires_at"])

    assert invitation.is_valid() is False


@pytest.mark.django_db
def test_is_valid_false_when_already_accepted(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.accept(username="newadmin", password="a-strong-passw0rd")

    assert invitation.is_valid() is False


@pytest.mark.django_db
def test_accept_creates_admin_user_scoped_to_school(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )

    user = invitation.accept(username="newadmin", password="a-strong-passw0rd")

    assert user.username == "newadmin"
    assert user.email == "new.admin@example.com"
    assert user.role == User.Role.ADMIN
    assert user.school == school
    assert user.is_school_admin() is True
    assert user.check_password("a-strong-passw0rd") is True


@pytest.mark.django_db
def test_accept_marks_invitation_as_accepted(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )

    invitation.accept(username="newadmin", password="a-strong-passw0rd")

    invitation.refresh_from_db()
    assert invitation.accepted_at is not None


@pytest.mark.django_db
def test_accept_raises_when_already_accepted(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.accept(username="newadmin", password="a-strong-passw0rd")

    with pytest.raises(ValueError):
        invitation.accept(username="someoneelse", password="another-strong-pw")


@pytest.mark.django_db
def test_accept_raises_when_expired(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.expires_at = timezone.now() - datetime.timedelta(days=1)
    invitation.save(update_fields=["expires_at"])

    with pytest.raises(ValueError):
        invitation.accept(username="newadmin", password="a-strong-passw0rd")


# --- revoke ----------------------------------------------------------------

@pytest.mark.django_db
def test_revoke_sets_revoked_at_and_invalidates(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )

    invitation.revoke()

    assert invitation.revoked_at is not None
    assert invitation.is_valid() is False


@pytest.mark.django_db
def test_revoke_raises_if_already_accepted(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.accept(username="newadmin", password="a-strong-passw0rd")

    with pytest.raises(ValueError):
        invitation.revoke()


@pytest.mark.django_db
def test_revoke_raises_if_already_revoked(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.revoke()

    with pytest.raises(ValueError):
        invitation.revoke()


@pytest.mark.django_db
def test_revoked_invitation_cannot_be_accepted(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.revoke()

    with pytest.raises(ValueError):
        invitation.accept(username="newadmin", password="a-strong-passw0rd")


# --- resend ------------------------------------------------------------------

@pytest.mark.django_db
def test_resend_extends_expiry_for_pending_invitation(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    original_expiry = invitation.expires_at

    invitation.resend()

    assert invitation.expires_at > original_expiry


@pytest.mark.django_db
def test_resend_extends_expiry_for_already_expired_invitation(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.expires_at = timezone.now() - datetime.timedelta(days=1)
    invitation.save(update_fields=["expires_at"])

    invitation.resend()

    assert invitation.is_valid() is True


@pytest.mark.django_db
def test_resend_raises_if_already_accepted(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.accept(username="newadmin", password="a-strong-passw0rd")

    with pytest.raises(ValueError):
        invitation.resend()


@pytest.mark.django_db
def test_resend_raises_if_revoked(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )
    invitation.revoke()

    with pytest.raises(ValueError):
        invitation.resend()


# --- role -------------------------------------------------------------------

@pytest.mark.django_db
def test_create_for_defaults_to_admin_role(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.admin@example.com", school=school, invited_by=platform_admin
    )

    assert invitation.role == User.Role.ADMIN


@pytest.mark.django_db
def test_teacher_invitation_accept_creates_teacher_user(school, platform_admin):
    invitation = SchoolAdminInvitation.create_for(
        email="new.teacher@example.com",
        school=school,
        invited_by=platform_admin,
        role=User.Role.TEACHER,
    )

    user = invitation.accept(username="newteacher", password="a-strong-passw0rd")

    assert user.role == User.Role.TEACHER
    assert user.is_teacher() is True
    assert user.school == school
