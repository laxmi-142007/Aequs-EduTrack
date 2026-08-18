from django.db import models
from django.utils import timezone
from students.models import Student
from schools.models import School


class BenefitType(models.TextChoices):
    BOOK = "BOOK", "Books"
    WORKBOOK = "WORKBOOK", "Workbook"
    STUDY_KIT = "STUDY_KIT", "Study Kit"
    LAPTOP = "LAPTOP", "Laptop"
    SCHOOL_ESSENTIAL = "SCHOOL_ESSENTIAL", "Government School Essential"


class RecipientType(models.TextChoices):
    STUDENT = "STUDENT", "Student"
    SCHOOL = "SCHOOL", "Government School"


class SchoolEssentialType(models.TextChoices):
    BENCHES = "BENCHES", "Benches"
    DESKS = "DESKS", "Desks"
    CHAIRS = "CHAIRS", "Chairs"
    WHITE_BOARDS = "WHITE_BOARDS", "White Boards"
    LIBRARY_BOOKS = "LIBRARY_BOOKS", "Library Books"
    LAB_EQUIPMENT = "LAB_EQUIPMENT", "Laboratory Equipment"
    WATER_FILTERS = "WATER_FILTERS", "Water Filters"
    FANS = "FANS", "Fans"
    SPORTS_KITS = "SPORTS_KITS", "Sports Kits"
    PROJECTORS = "PROJECTORS", "Projectors"
    OTHER = "OTHER", "Other Educational Resources"


class StudyKit(models.Model):
    """Configurable Study Kit Definition"""
    name = models.CharField(max_length=200, unique=True, help_text="e.g. Primary STEM Kit, High School Kit, PUC Science Kit")
    target_grade_level = models.CharField(
        max_length=100,
        default="Class 1 to 2nd PUC",
        help_text="e.g. Class 1-5, Class 6-10, 1st PUC & 2nd PUC",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.target_grade_level})"


class StudyKitItem(models.Model):
    """Sub-items contained within a Study Kit"""
    kit = models.ForeignKey(
        StudyKit,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_name = models.CharField(max_length=150, help_text="e.g. Geometry Box, 6 Long Notebooks, Drawing Pad, Color Pencils")
    quantity_per_kit = models.PositiveIntegerField(default=1)
    specification = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.quantity_per_kit}x {self.item_name} (in {self.kit.name})"


class Distribution(models.Model):
    BenefitType = BenefitType
    RecipientType = RecipientType
    SchoolEssentialType = SchoolEssentialType

    benefit_type = models.CharField(
        max_length=30,
        choices=BenefitType.choices,
    )
    class BenefitType(models.TextChoices):
        BOOK = "BOOK", "Books"
        WORKBOOK = "WORKBOOK", "Workbook"
        STUDY_KIT = "STUDY_KIT", "Study Kit"
        LAPTOP = "LAPTOP", "Laptop"
        INTERNSHIP = "INTERNSHIP", "Internship"

    recipient_type = models.CharField(
        max_length=20,
        choices=RecipientType.choices,
        default=RecipientType.STUDENT,
    )

    # Student beneficiary (for student-level distributions: Books, Workbooks, Study Kits, Laptops)
    student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="distributions",
    )

    # School recipient (for school essentials or school-level aggregate distributions)
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="school_distributions",
    )

    # Linked physical inventory item (for real-time stock sync)
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="distributions",
    )

    # Specific school essential item type (for Module 12)
    essential_item_type = models.CharField(
        max_length=30,
        choices=SchoolEssentialType.choices,
        null=True,
        blank=True,
    )

    # Linked Study Kit definition (for Module 8)
    study_kit = models.ForeignKey(
        StudyKit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="distributions",
    )

    academic_year = models.CharField(
        max_length=20,
        default="2026-27",
        help_text="Example: 2026-27",
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    distribution_date = models.DateField(
        default=timezone.localdate,
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
        ordering = ["-distribution_date", "-created_at"]
        verbose_name = "Distribution Record"
        verbose_name_plural = "Distribution Records"

    def __str__(self):
        recipient = self.student.student_name if self.student else (self.school.name if self.school else "General")
        return (
            f"{recipient} - "
            f"{self.get_benefit_type_display()} - "
            f"{self.quantity} unit(s) - "
            f"{self.academic_year}"
        )
