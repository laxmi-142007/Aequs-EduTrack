from django.db import models
from students.models import Student


class Distribution(models.Model):

    class BenefitType(models.TextChoices):
        BOOK = "BOOK", "Books"
        WORKBOOK = "WORKBOOK", "Workbook"
        STUDY_KIT = "STUDY_KIT", "Study Kit"

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="distributions",
    )

    benefit_type = models.CharField(
        max_length=30,
        choices=BenefitType.choices,
    )

    academic_year = models.CharField(
        max_length=20,
        help_text="Example: 2026-27",
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    distribution_date = models.DateField(
        auto_now_add=True,
    )

    issued_by = models.CharField(
        max_length=150,
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
        ordering = ["-distribution_date"]

    def __str__(self):
        return (
            f"{self.student.student_name} - "
            f"{self.get_benefit_type_display()} - "
            f"{self.academic_year}"
        )