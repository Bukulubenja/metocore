import pytest

from accounts.models import User
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
def test_admin_can_set_teacher_title(client, school_admin, teacher):
    client.force_login(school_admin)

    response = client.post(
        f"/teachers/{teacher.id}/title/", {"title": "Head Teacher"}
    )

    assert response.status_code == 302
    teacher.refresh_from_db()
    assert teacher.title == "Head Teacher"


@pytest.mark.django_db
def test_teacher_cannot_set_own_title(client, teacher):
    client.force_login(teacher)

    response = client.post(
        f"/teachers/{teacher.id}/title/", {"title": "Head Teacher"}
    )

    assert response.status_code == 403
    teacher.refresh_from_db()
    assert teacher.title == ""


@pytest.mark.django_db
def test_setting_title_for_other_schools_teacher_404s(client, school_admin, other_school):
    other_teacher = User.objects.create_user(
        username="other", password="x", role=User.Role.TEACHER, school=other_school
    )
    client.force_login(school_admin)

    response = client.post(
        f"/teachers/{other_teacher.id}/title/", {"title": "Head Teacher"}
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_teacher_title_shown_on_teacher_list(client, school_admin, teacher):
    teacher.title = "Class Teacher"
    teacher.save(update_fields=["title"])
    client.force_login(school_admin)

    response = client.get("/teachers/")

    assert response.status_code == 200
    assert b"Class Teacher" in response.content
