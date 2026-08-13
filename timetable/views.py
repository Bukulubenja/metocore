import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from schools.models import Term
from timetable.models import LessonRequirement, Period, SchoolClass, Subject, TeacherAvailability, TimetableEntry
from timetable.solver import TimetableGenerationError, generate_timetable


def _require_school_admin(request) -> None:
    if not request.user.is_school_admin():
        raise PermissionDenied("Only school admins can manage the timetable.")


def _parse_period_fields(post):
    errors = []

    name = post.get("name", "").strip()
    if not name:
        errors.append("Period name is required.")

    day_of_week = None
    try:
        day_of_week = int(post.get("day_of_week", ""))
        if day_of_week not in dict(Period.DayOfWeek.choices):
            errors.append("Choose a valid day.")
            day_of_week = None
    except ValueError:
        errors.append("Choose a valid day.")

    start_time = None
    try:
        start_time = datetime.time.fromisoformat(post.get("start_time", ""))
    except ValueError:
        errors.append("Start time must be a valid time.")

    end_time = None
    try:
        end_time = datetime.time.fromisoformat(post.get("end_time", ""))
    except ValueError:
        errors.append("End time must be a valid time.")

    if start_time and end_time and end_time <= start_time:
        errors.append("End time must be after the start time.")

    is_teaching_period = post.get("is_teaching_period") == "on"

    return name, day_of_week, start_time, end_time, is_teaching_period, errors


@login_required
def manage_periods(request):
    _require_school_admin(request)
    school = request.user.school

    if request.method == "POST":
        name, day_of_week, start_time, end_time, is_teaching_period, errors = (
            _parse_period_fields(request.POST)
        )
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            Period.objects.create(
                school=school,
                name=name,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                is_teaching_period=is_teaching_period,
            )
            messages.success(request, f"Added period '{name}'.")
        return redirect("timetable-period-list")

    periods = school.periods.all()
    return render(
        request,
        "timetable/period_list.html",
        {"periods": periods, "day_choices": Period.DayOfWeek.choices},
    )


@login_required
def period_edit(request, period_id):
    _require_school_admin(request)
    period = get_object_or_404(Period, pk=period_id, school=request.user.school)

    if request.method == "POST":
        name, day_of_week, start_time, end_time, is_teaching_period, errors = (
            _parse_period_fields(request.POST)
        )
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("timetable-period-edit", period_id=period.id)

        period.name = name
        period.day_of_week = day_of_week
        period.start_time = start_time
        period.end_time = end_time
        period.is_teaching_period = is_teaching_period
        period.save()
        messages.success(request, f"Updated period '{name}'.")
        return redirect("timetable-period-list")

    return render(
        request,
        "timetable/period_edit.html",
        {"period": period, "day_choices": Period.DayOfWeek.choices},
    )


@login_required
def period_delete(request, period_id):
    _require_school_admin(request)
    period = get_object_or_404(Period, pk=period_id, school=request.user.school)

    if request.method == "POST":
        period.delete()
        messages.success(request, "Period deleted.")

    return redirect("timetable-period-list")


@login_required
def manage_subjects(request):
    _require_school_admin(request)
    school = request.user.school

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        if name and code:
            Subject.objects.create(school=school, name=name, code=code)
            messages.success(request, f"Added subject '{name}'.")
        else:
            messages.error(request, "Name and code are required.")
        return redirect("timetable-subject-list")

    subjects = school.subjects.all()
    return render(request, "timetable/subject_list.html", {"subjects": subjects})


@login_required
def subject_edit(request, subject_id):
    _require_school_admin(request)
    subject = get_object_or_404(Subject, pk=subject_id, school=request.user.school)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip()
        if name and code:
            subject.name = name
            subject.code = code
            subject.save()
            messages.success(request, f"Updated subject '{name}'.")
            return redirect("timetable-subject-list")
        messages.error(request, "Name and code are required.")
        return redirect("timetable-subject-edit", subject_id=subject.id)

    return render(request, "timetable/subject_edit.html", {"subject": subject})


@login_required
def subject_delete(request, subject_id):
    _require_school_admin(request)
    subject = get_object_or_404(Subject, pk=subject_id, school=request.user.school)

    if request.method == "POST":
        subject.delete()
        messages.success(request, "Subject deleted.")

    return redirect("timetable-subject-list")


@login_required
def manage_classes(request):
    _require_school_admin(request)
    school = request.user.school

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        allows_parallel_lessons = request.POST.get("allows_parallel_lessons") == "on"
        if name:
            SchoolClass.objects.create(
                school=school, name=name, allows_parallel_lessons=allows_parallel_lessons
            )
            messages.success(request, f"Added class '{name}'.")
        else:
            messages.error(request, "Class name is required.")
        return redirect("timetable-class-list")

    classes = school.classes.all()
    return render(request, "timetable/class_list.html", {"classes": classes})


@login_required
def class_edit(request, class_id):
    _require_school_admin(request)
    school_class = get_object_or_404(SchoolClass, pk=class_id, school=request.user.school)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        allows_parallel_lessons = request.POST.get("allows_parallel_lessons") == "on"
        if name:
            school_class.name = name
            school_class.allows_parallel_lessons = allows_parallel_lessons
            school_class.save()
            messages.success(request, f"Updated class '{name}'.")
            return redirect("timetable-class-list")
        messages.error(request, "Class name is required.")
        return redirect("timetable-class-edit", class_id=school_class.id)

    return render(request, "timetable/class_edit.html", {"school_class": school_class})


@login_required
def class_delete(request, class_id):
    _require_school_admin(request)
    school_class = get_object_or_404(SchoolClass, pk=class_id, school=request.user.school)

    if request.method == "POST":
        school_class.delete()
        messages.success(request, "Class deleted.")

    return redirect("timetable-class-list")


@login_required
def manage_teacher_availability(request):
    _require_school_admin(request)
    school = request.user.school
    teachers = User.objects.filter(school=school, role=User.Role.TEACHER)

    selected_teacher = None
    teacher_id = request.POST.get("teacher_id") or request.GET.get("teacher_id")
    if teacher_id:
        selected_teacher = get_object_or_404(User, pk=teacher_id, school=school, role=User.Role.TEACHER)

    if request.method == "POST" and selected_teacher:
        period_ids = {int(pid) for pid in request.POST.getlist("period_ids")}
        TeacherAvailability.objects.filter(teacher=selected_teacher, period__school=school).delete()
        TeacherAvailability.objects.bulk_create(
            [
                TeacherAvailability(teacher=selected_teacher, period_id=period_id)
                for period_id in period_ids
            ]
        )
        messages.success(request, f"Updated availability for {selected_teacher.username}.")
        return redirect(f"/timetable/availability/?teacher_id={selected_teacher.id}")

    periods = school.periods.filter(is_teaching_period=True)
    available_period_ids = set()
    if selected_teacher:
        available_period_ids = set(
            TeacherAvailability.objects.filter(teacher=selected_teacher).values_list(
                "period_id", flat=True
            )
        )

    return render(
        request,
        "timetable/teacher_availability.html",
        {
            "teachers": teachers,
            "selected_teacher": selected_teacher,
            "periods": periods,
            "available_period_ids": available_period_ids,
        },
    )


@login_required
def manage_lesson_requirements(request):
    _require_school_admin(request)
    school = request.user.school

    if request.method == "POST":
        teacher = get_object_or_404(
            User, pk=request.POST.get("teacher_id"), school=school, role=User.Role.TEACHER
        )
        subject = get_object_or_404(Subject, pk=request.POST.get("subject_id"), school=school)
        school_class = get_object_or_404(
            SchoolClass, pk=request.POST.get("school_class_id"), school=school
        )
        try:
            periods_per_week = int(request.POST.get("periods_per_week", ""))
            if periods_per_week <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "Periods per week must be a positive whole number.")
            return redirect("timetable-requirement-list")

        LessonRequirement.objects.create(
            teacher=teacher,
            subject=subject,
            school_class=school_class,
            periods_per_week=periods_per_week,
        )
        messages.success(
            request, f"Added {subject.code} for {school_class.name} — {teacher.username}."
        )
        return redirect("timetable-requirement-list")

    requirements = LessonRequirement.objects.filter(school_class__school=school).select_related(
        "teacher", "subject", "school_class"
    )
    return render(
        request,
        "timetable/requirement_list.html",
        {
            "requirements": requirements,
            "teachers": User.objects.filter(school=school, role=User.Role.TEACHER),
            "subjects": school.subjects.all(),
            "classes": school.classes.all(),
        },
    )


@login_required
def requirement_edit(request, requirement_id):
    _require_school_admin(request)
    school = request.user.school
    requirement = get_object_or_404(
        LessonRequirement, pk=requirement_id, school_class__school=school
    )

    if request.method == "POST":
        teacher = get_object_or_404(
            User, pk=request.POST.get("teacher_id"), school=school, role=User.Role.TEACHER
        )
        subject = get_object_or_404(Subject, pk=request.POST.get("subject_id"), school=school)
        school_class = get_object_or_404(
            SchoolClass, pk=request.POST.get("school_class_id"), school=school
        )
        try:
            periods_per_week = int(request.POST.get("periods_per_week", ""))
            if periods_per_week <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "Periods per week must be a positive whole number.")
            return redirect("timetable-requirement-edit", requirement_id=requirement.id)

        requirement.teacher = teacher
        requirement.subject = subject
        requirement.school_class = school_class
        requirement.periods_per_week = periods_per_week
        requirement.save()
        messages.success(request, "Updated lesson requirement.")
        return redirect("timetable-requirement-list")

    return render(
        request,
        "timetable/requirement_edit.html",
        {
            "requirement": requirement,
            "teachers": User.objects.filter(school=school, role=User.Role.TEACHER),
            "subjects": school.subjects.all(),
            "classes": school.classes.all(),
        },
    )


@login_required
def requirement_delete(request, requirement_id):
    _require_school_admin(request)
    requirement = get_object_or_404(
        LessonRequirement, pk=requirement_id, school_class__school=request.user.school
    )

    if request.method == "POST":
        requirement.delete()
        messages.success(request, "Lesson requirement deleted.")

    return redirect("timetable-requirement-list")


@login_required
def generate_timetable_view(request):
    _require_school_admin(request)
    school = request.user.school

    if request.method == "POST":
        term = get_object_or_404(Term, pk=request.POST.get("term_id"), school=school)
        try:
            entries = generate_timetable(school=school, term=term)
        except TimetableGenerationError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Generated {len(entries)} lessons for {term.name}.")
            return redirect(f"/timetable/?term_id={term.id}")

    terms = school.terms.all()
    return render(request, "timetable/generate.html", {"terms": terms})


@login_required
def timetable_view(request):
    _require_school_admin(request)
    school = request.user.school

    term_id = request.GET.get("term_id")
    term = None
    if term_id:
        term = get_object_or_404(Term, pk=term_id, school=school)
    else:
        term = Term.objects.current_for(school) or school.terms.first()

    entries = []
    if term:
        entries = TimetableEntry.objects.filter(term=term, school_class__school=school).select_related(
            "school_class", "period", "subject", "teacher"
        )

    classes = school.classes.all()
    periods = school.periods.filter(is_teaching_period=True)

    grid = {school_class.id: {period.id: [] for period in periods} for school_class in classes}
    for entry in entries:
        grid.setdefault(entry.school_class_id, {}).setdefault(entry.period_id, []).append(entry)

    return render(
        request,
        "timetable/timetable_view.html",
        {
            "term": term,
            "terms": school.terms.all(),
            "classes": classes,
            "periods": periods,
            "grid": grid,
        },
    )


@login_required
def timetable_entry_edit(request, entry_id):
    _require_school_admin(request)
    school = request.user.school
    entry = get_object_or_404(TimetableEntry, pk=entry_id, school_class__school=school)

    if request.method == "POST":
        teacher = get_object_or_404(
            User, pk=request.POST.get("teacher_id"), school=school, role=User.Role.TEACHER
        )
        subject = get_object_or_404(Subject, pk=request.POST.get("subject_id"), school=school)

        entry.teacher = teacher
        entry.subject = subject
        try:
            with transaction.atomic():
                entry.save()
        except IntegrityError:
            messages.error(
                request,
                f"{teacher.username} already has another lesson in this period — pick a "
                "different teacher or period.",
            )
            return redirect("timetable-entry-edit", entry_id=entry.id)

        messages.success(request, "Updated lesson.")
        return redirect(f"/timetable/?term_id={entry.term_id}")

    return render(
        request,
        "timetable/entry_edit.html",
        {
            "entry": entry,
            "teachers": User.objects.filter(school=school, role=User.Role.TEACHER),
            "subjects": school.subjects.all(),
        },
    )


@login_required
def my_timetable(request):
    if not request.user.is_teacher():
        raise PermissionDenied("Only teachers can view their own timetable.")

    school = request.user.school
    term = Term.objects.current_for(school) if school else None
    entries = []
    if term:
        entries = TimetableEntry.objects.filter(term=term, teacher=request.user).select_related(
            "school_class", "period", "subject"
        )

    return render(
        request, "timetable/my_timetable.html", {"term": term, "entries": entries}
    )
