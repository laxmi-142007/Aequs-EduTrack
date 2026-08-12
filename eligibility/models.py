from django.db import models
from students.models import Student


class BenefitType(models.TextChoices):
    BOOK = "BOOK", "Books"
    WORKBOOK = "WORKBOOK", "Workbook"
    STUDY_KIT = "STUDY_KIT", "Study Kit"
    LAPTOP = "LAPTOP", "Laptop"
    INTERNSHIP = "INTERNSHIP", "Internship"


class EligibilityRecord(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="eligibility_records",
    )

    benefit_type = models.CharField(
        max_length=30,
        choices=BenefitType.choices,
    )

    academic_year = models.CharField(
        max_length=20,
    )

    eligible = models.BooleanField(
        default=False,
    )

    selection_rank = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    reason = models.TextField(
        blank=True,
    )

    checked_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        unique_together = (
            "student",
            "benefit_type",
            "academic_year",
        )

    def __str__(self):
        return (
            f"{self.student.student_name} - "
            f"{self.get_benefit_type_display()} - "
            f"{self.academic_year}"
        )