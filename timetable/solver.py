from ortools.sat.python import cp_model

from timetable.models import LessonRequirement, Period, TeacherAvailability, TimetableEntry


class TimetableGenerationError(Exception):
    pass


def generate_timetable(*, school, term):
    """Generate a collision-free timetable for the given school/term.

    Returns the list of created TimetableEntry objects.
    Raises TimetableGenerationError if no feasible solution exists.
    """
    requirements = list(
        LessonRequirement.objects.filter(school_class__school=school).select_related(
            "teacher", "subject", "school_class"
        )
    )
    if not requirements:
        raise TimetableGenerationError("No lesson requirements are set up yet.")

    periods = list(Period.objects.filter(school=school, is_teaching_period=True))
    if not periods:
        raise TimetableGenerationError("No teaching periods are set up yet.")

    availability = set(
        TeacherAvailability.objects.filter(period__school=school).values_list(
            "teacher_id", "period_id"
        )
    )

    model = cp_model.CpModel()
    x = {}

    for req in requirements:
        eligible_periods = [p for p in periods if (req.teacher_id, p.id) in availability]
        if len(eligible_periods) < req.periods_per_week:
            raise TimetableGenerationError(
                f"{req.teacher.username} doesn't have enough available periods for "
                f"{req.subject.code} — {req.school_class.name} (needs "
                f"{req.periods_per_week}/week, only {len(eligible_periods)} available)."
            )

        for period in eligible_periods:
            x[req.id, period.id] = model.NewBoolVar(f"x_{req.id}_{period.id}")

        model.Add(
            sum(x[req.id, period.id] for period in eligible_periods)
            == req.periods_per_week
        )

    for period in periods:
        by_teacher = {}
        by_class = {}
        for req in requirements:
            key = (req.id, period.id)
            if key not in x:
                continue
            by_teacher.setdefault(req.teacher_id, []).append(x[key])
            if not req.school_class.allows_parallel_lessons:
                by_class.setdefault(req.school_class_id, []).append(x[key])

        for lesson_vars in by_teacher.values():
            if len(lesson_vars) > 1:
                model.Add(sum(lesson_vars) <= 1)
        for lesson_vars in by_class.values():
            if len(lesson_vars) > 1:
                model.Add(sum(lesson_vars) <= 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20.0
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise TimetableGenerationError(
            "Couldn't fit all requirements into the available periods — try "
            "widening teacher availability or reducing periods/week."
        )

    TimetableEntry.objects.filter(term=term, school_class__school=school).delete()

    entries = [
        TimetableEntry(
            term=term,
            school_class=req.school_class,
            period=period,
            subject=req.subject,
            teacher=req.teacher,
        )
        for req in requirements
        for period in periods
        if (req.id, period.id) in x and solver.Value(x[req.id, period.id])
    ]
    TimetableEntry.objects.bulk_create(entries)
    return entries
