from django.conf import settings
from django.db import models


class Period(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"

    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="periods"
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_teaching_period = models.BooleanField(default=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]

    def __str__(self) -> str:
        return f"{self.get_day_of_week_display()} {self.name}"


class Subject(models.Model):
    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="subjects"
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class SchoolClass(models.Model):
    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="classes"
    )
    name = models.CharField(max_length=50)
    allows_parallel_lessons = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class TeacherAvailability(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="timetable_availability",
    )
    period = models.ForeignKey(
        Period, on_delete=models.CASCADE, related_name="available_teachers"
    )

    class Meta:
        unique_together = [("teacher", "period")]

    def __str__(self) -> str:
        return f"{self.teacher.username} available {self.period}"


class LessonRequirement(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_requirements",
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="lesson_requirements"
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="lesson_requirements"
    )
    periods_per_week = models.PositiveIntegerField()

    class Meta:
        ordering = ["school_class__name", "subject__name"]

    def __str__(self) -> str:
        return (
            f"{self.teacher.username} — {self.subject.code} — "
            f"{self.school_class.name} ({self.periods_per_week}/wk)"
        )


class TimetableEntry(models.Model):
    term = models.ForeignKey(
        "schools.Term", on_delete=models.CASCADE, related_name="timetable_entries"
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="timetable_entries"
    )
    period = models.ForeignKey(
        Period, on_delete=models.CASCADE, related_name="timetable_entries"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="timetable_entries"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="timetable_entries",
    )

    class Meta:
        unique_together = [("teacher", "period", "term")]
        ordering = ["period__day_of_week", "period__start_time"]

    def __str__(self) -> str:
        return f"{self.school_class.name} — {self.subject.code} — {self.period}"
