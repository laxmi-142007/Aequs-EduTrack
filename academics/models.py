from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import re

from django.db import models, transaction

from students.models import Student


# ============================================================================
# ACADEMIC YEAR HELPER
# ============================================================================

def get_current_academic_year():
    """
    Automatically determine the current academic year.

    Academic year starts in June.

    Examples:
        June 2026      -> 2026-27
        December 2026  -> 2026-27
        May 2027       -> 2026-27
        June 2027      -> 2027-28
    """

    today = date.today()

    if today.month >= 6:
        start_year = today.year
    else:
        start_year = today.year - 1

    return f"{start_year}-{str(start_year + 1)[-2:]}"


# ============================================================================
# COURSE / CLASS MASTER
# ============================================================================

class CourseMaster(models.Model):

    class Category(models.TextChoices):
        SCHOOL = "SCHOOL", "School"
        PUC = "PUC", "Pre-University"
        DIPLOMA = "DIPLOMA", "Diploma"
        DEGREE = "DEGREE", "Degree"
        PG = "PG", "Post Graduation"
        PROFESSIONAL = "PROFESSIONAL", "Professional"

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            "category",
            "display_order",
            "name",
        ]

    def __str__(self):
        return self.name


# ============================================================================
# ACADEMIC RECORD
# ============================================================================

class AcademicRecord(models.Model):

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="academic_records",
    )

    academic_year = models.CharField(
        max_length=20,
        default=get_current_academic_year,
        help_text="Example: 2026-27",
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

    # ========================================================================
    # ACADEMIC YEAR
    # ========================================================================

    @staticmethod
    def _academic_year_start(year):
        """
        Convert:

            2026-27 -> 2026
            2025-26 -> 2025
        """

        if not year:
            return None

        match = re.match(
            r"^\s*(\d{4})",
            str(year),
        )

        if match:
            return int(match.group(1))

        return None

    # ========================================================================
    # PERCENTAGE
    # ========================================================================

    def _calculate_percentage(self):
        """
        Calculate percentage from obtained and total marks.
        """

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

    # ========================================================================
    # PREVIOUS CLASS
    # ========================================================================

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

    # ========================================================================
    # NEXT CLASS
    # ========================================================================

    @staticmethod
    def _get_next_class(current_class):
        """
        Return the next class/course.

        Supported examples:

            Class 1 -> Class 2
            Class 5 -> Class 6
            Class 9 -> Class 10
            Class 10 -> Class 11
            Class 11 -> Class 12
            Class 12 -> None

            1st PU -> 2nd PU
            2nd PU -> None

            BE 1st year -> BE 2nd year
            BE 2nd year -> BE 3rd year
            BE 3rd year -> BE 4th year
            BE 4th year -> None

            Diploma 1st year -> Diploma 2nd year
            Diploma 2nd year -> Diploma 3rd year
            Diploma 3rd year -> None

            ITI 1st year -> ITI 2nd year
            ITI 2nd year -> ITI 3rd year
            ITI 3rd year -> None
        """

        if not current_class:
            return None

        value = str(current_class).strip()

        # --------------------------------------------------------------------
        # Numeric classes
        # --------------------------------------------------------------------

        match = re.match(
            r"^(?:Class\s*)?(\d+)$",
            value,
            re.IGNORECASE,
        )

        if match:

            class_number = int(
                match.group(1)
            )

            # Do not promote Class 12.
            if class_number >= 12:
                return None

            next_class = class_number + 1

            if value.lower().startswith("class"):
                return f"Class {next_class}"

            return str(next_class)

        # --------------------------------------------------------------------
        # PU
        # --------------------------------------------------------------------

        normalized = re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

        pu_match = re.match(
            r"^(\d+)(?:st|nd|rd|th)\s*PU$",
            normalized,
            re.IGNORECASE,
        )

        if pu_match:

            year = int(
                pu_match.group(1)
            )

            if year == 1:
                return "2nd PU"

            return None

        # --------------------------------------------------------------------
        # Engineering / Degree / Diploma / ITI
        # --------------------------------------------------------------------

        course_match = re.match(
            r"^(.*?)(?:\s+)(\d+)(?:st|nd|rd|th)\s+year$",
            normalized,
            re.IGNORECASE,
        )

        if course_match:

            course_name = course_match.group(1).strip()

            year = int(
                course_match.group(2)
            )

            course_lower = course_name.lower()

            # Known 4-year courses
            if course_lower in [
                "be",
                "b.e.",
                "btech",
                "b.tech",
                "b.sc",
                "bsc",
            ]:
                max_year = 4

            # Diploma
            elif "diploma" in course_lower:
                max_year = 3

            # ITI
            elif "iti" in course_lower:
                max_year = 3

            # Other degree/course
            else:
                max_year = 4

            if year >= max_year:
                return None

            next_year = year + 1

            if next_year == 1:
                suffix = "st"
            elif next_year == 2:
                suffix = "nd"
            elif next_year == 3:
                suffix = "rd"
            else:
                suffix = "th"

            return (
                f"{course_name} "
                f"{next_year}{suffix} year"
            )

        return None

    # ========================================================================
    # AUTOMATIC PROMOTION
    # ========================================================================

    def _promote_student(self):
        """
        Automatically update the student's current class/course
        when the academic record is marked as Promoted.

        Examples:

            Class 5 -> Class 6
            Class 10 -> Class 11
            1st PU -> 2nd PU
            BE 2nd year -> BE 3rd year
        """

        status = (
            self.promotion_status or ""
        ).strip().lower()

        if status != "promoted":
            return

        next_class = self._get_next_class(
            self.class_or_course
        )

        if not next_class:
            return

        student = self.student

        if student.current_class != next_class:

            student.current_class = next_class

            student.save(
                update_fields=[
                    "current_class",
                    "updated_at",
                ]
            )

    # ========================================================================
    # SAVE
    # ========================================================================

    def save(self, *args, **kwargs):
        """
        Automatically:

        1. Calculate percentage.
        2. Calculate previous class.
        3. Save academic record.
        4. Promote student if status is Promoted.
        5. Recalculate ranks.
        """

        # --------------------------------------------------------------------
        # Calculate percentage
        # --------------------------------------------------------------------

        if (
            self.marks_obtained is not None
            and self.total_marks is not None
        ):
            self.percentage = (
                self._calculate_percentage()
            )

        # --------------------------------------------------------------------
        # Calculate previous class
        # --------------------------------------------------------------------

        if not self.previous_class:
            self.previous_class = (
                self._calculate_previous_class()
            )

        # --------------------------------------------------------------------
        # Rank will be recalculated after saving
        # --------------------------------------------------------------------

        self.rank = None

        # --------------------------------------------------------------------
        # Save + promotion in one transaction
        # --------------------------------------------------------------------

        with transaction.atomic():

            super().save(*args, **kwargs)

            self._promote_student()

        # --------------------------------------------------------------------
        # Recalculate ranks
        # --------------------------------------------------------------------

        self._update_ranks()

    # ========================================================================
    # RANK CALCULATION
    # ========================================================================

    def _update_ranks(self):
        """
        Calculate rank among students from the same:

            School
            Academic year
            Class/course

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
            ).update(
                rank=None
            )

            return

        records = (
            AcademicRecord.objects
            .filter(
                academic_year=self.academic_year,
                class_or_course=self.class_or_course,
                student__school=self.student.school,
                percentage__isnull=False,
            )
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

        # Refresh this object.
        self.refresh_from_db(
            fields=[
                "percentage",
                "previous_class",
                "rank",
            ]
        )


# ============================================================================
# SUBJECT SCORE MODEL (Module 3: Separate Subject Tracking & Academics)
# ============================================================================

class SubjectScore(models.Model):
    """
    Individual subject-level marks and evaluation breakdown
    for student academic records.
    """
    class ExamType(models.TextChoices):
        UNIT_TEST = "UNIT_TEST", "Unit Test"
        MIDTERM = "MIDTERM", "Midterm Examination"
        ANNUAL = "ANNUAL", "Annual Examination"
        DIAGNOSTIC = "DIAGNOSTIC", "Diagnostic Assessment"

    academic_record = models.ForeignKey(
        AcademicRecord,
        on_delete=models.CASCADE,
        related_name="subject_scores",
    )
    subject_name = models.CharField(
        max_length=100,
        help_text="e.g. Mathematics, Science, English, Regional Language, Social Science",
    )
    exam_type = models.CharField(
        max_length=30,
        choices=ExamType.choices,
        default=ExamType.ANNUAL,
    )
    marks_obtained = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )
    max_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    grade = models.CharField(
        max_length=10,
        blank=True,
        help_text="e.g. A+, A, B, C, D",
    )
    remarks = models.CharField(
        max_length=200,
        blank=True,
    )

    class Meta:
        ordering = ["subject_name", "exam_type"]
        unique_together = ["academic_record", "subject_name", "exam_type"]

    def __str__(self):
        return f"{self.subject_name} ({self.get_exam_type_display()}): {self.marks_obtained}/{self.max_marks}"

    def save(self, *args, **kwargs):
        if self.max_marks and self.max_marks > 0:
            self.percentage = round((self.marks_obtained / self.max_marks) * 100, 2)
            if self.percentage >= 90:
                self.grade = "A+"
            elif self.percentage >= 80:
                self.grade = "A"
            elif self.percentage >= 70:
                self.grade = "B+"
            elif self.percentage >= 60:
                self.grade = "B"
            elif self.percentage >= 50:
                self.grade = "C"
            elif self.percentage >= 35:
                self.grade = "D"
            else:
                self.grade = "F"
        super().save(*args, **kwargs)