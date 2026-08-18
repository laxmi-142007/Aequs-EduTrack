from decimal import Decimal, ROUND_HALF_UP
import re

from django.db import models
from students.models import Student


class AcademicRecord(models.Model):

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="academic_records",
    )

    academic_year = models.CharField(
        max_length=20,
        help_text="Example: 2025-26",
    )

    class_or_course = models.CharField(
        max_length=50,
        help_text="Example: Class 10, 2nd PUC, 3rd Year Diploma",
    )

    marks_obtained = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    total_marks = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    rank = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    previous_class = models.CharField(
        max_length=50,
        blank=True,
    )

    promotion_status = models.CharField(
        max_length=50,
        blank=True,
    )

    transfer_school = models.CharField(
        max_length=200,
        blank=True,
    )

    remarks = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-academic_year"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "student",
                    "academic_year",
                    "class_or_course",
                ],
                name="unique_student_academic_course_year",
            ),
        ]

    def __str__(self):
        return (
            f"{self.student.student_name} - "
            f"{self.academic_year} - "
            f"{self.class_or_course}"
        )

    @staticmethod
    def _academic_year_start(year):
        """
        Convert academic year such as:
            2025-26 -> 2025

        Used to determine which academic record is previous.
        """
        if not year:
            return None

        match = re.match(r"^\s*(\d{4})", str(year))

        if match:
            return int(match.group(1))

        return None

    def _calculate_percentage(self):
        """Calculate percentage from obtained and total marks."""

        if (
            self.marks_obtained is None
            or self.total_marks is None
            or self.total_marks <= 0
        ):
            return None

        percentage = (
            Decimal(str(self.marks_obtained))
            * Decimal("100")
            / Decimal(str(self.total_marks))
        )

        return percentage.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    def _calculate_previous_class(self):
        """
        Find the student's most recent academic record
        before the current academic year.
        """

        current_year = self._academic_year_start(
            self.academic_year
        )

        records = (
            AcademicRecord.objects
            .filter(student=self.student)
            .exclude(pk=self.pk)
        )

        previous_record = None
        previous_year = None

        for record in records:
            record_year = self._academic_year_start(
                record.academic_year
            )

            if record_year is None:
                continue

            if current_year is not None:
                if record_year >= current_year:
                    continue

            if (
                previous_year is None
                or record_year > previous_year
            ):
                previous_year = record_year
                previous_record = record

        if previous_record:
            return previous_record.class_or_course

        return ""

    def save(self, *args, **kwargs):
        """
        Automatically calculate percentage and previous class
        whenever an academic record is saved.
        """

        # Only calculate percentage when marks are supplied.
        # Otherwise preserve an explicitly provided percentage.
        if self.marks_obtained is not None and self.total_marks is not None:
            self.percentage = self._calculate_percentage()

        # Calculate previous class only when not explicitly supplied.
        if not self.previous_class:
            self.previous_class = self._calculate_previous_class()

        # Rank is calculated after the record has been saved.
        self.rank = None

        super().save(*args, **kwargs)

        self._update_ranks()

    def _update_ranks(self):
        """
        Calculate rank among students from the same school,
        academic year and class/course.

        Higher percentage = better rank.

        Example:
            98% -> Rank 1
            95% -> Rank 2
            95% -> Rank 2
            90% -> Rank 4
        """

        if self.percentage is None:
            AcademicRecord.objects.filter(
                pk=self.pk
            ).update(rank=None)
            return

        records = AcademicRecord.objects.filter(
            academic_year=self.academic_year,
            class_or_course=self.class_or_course,
            student__school=self.student.school,
            percentage__isnull=False,
        )

        for record in records:
            better_count = records.filter(
                percentage__gt=record.percentage
            ).count()

            AcademicRecord.objects.filter(
                pk=record.pk
            ).update(
                rank=better_count + 1
            )

        # Refresh this object so its rank is immediately available.
        self.refresh_from_db(
            fields=["percentage", "previous_class", "rank"]
        )
