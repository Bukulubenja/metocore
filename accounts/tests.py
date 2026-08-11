import pytest
from django.core.exceptions import ValidationError

from accounts.models import User


@pytest.mark.django_db
def test_user_defaults_to_teacher_role():
    user = User.objects.create_user(username="jdoe", password="x")

    assert user.role == User.Role.TEACHER


@pytest.mark.django_db
def test_is_teacher_true_for_teacher_role():
    user = User.objects.create_user(username="jdoe", password="x", role=User.Role.TEACHER)

    assert user.is_teacher() is True
    assert user.is_school_admin() is False


@pytest.mark.django_db
def test_is_school_admin_true_for_admin_role():
    admin = User.objects.create_user(username="principal", password="x", role=User.Role.ADMIN)

    assert admin.is_school_admin() is True
    assert admin.is_teacher() is False


@pytest.mark.django_db
def test_invalid_role_rejected_by_full_clean():
    user = User(username="baduser", role="NOT_A_ROLE")

    with pytest.raises(ValidationError):
        user.full_clean()
