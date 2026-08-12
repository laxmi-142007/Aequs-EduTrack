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
        help_text="Example: Class 10, 2nd PUC, Degree",
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

    def __str__(self):
        return (
            f"{self.student.student_name} - "
            f"{self.academic_year} - "
            f"{self.class_or_course}"
        )