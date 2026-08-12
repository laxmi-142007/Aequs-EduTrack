from django.db import models
from schools.models import School


class Student(models.Model):

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        TRANSFERRED = "TRANSFERRED", "Transferred"
        PASSED_OUT = "PASSED_OUT", "Passed Out"
        INACTIVE = "INACTIVE", "Inactive"

    admission_number = models.CharField(
        max_length=50,
        unique=True,
    )

    student_name = models.CharField(
        max_length=150,
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
    )

    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
    )

    photo = models.ImageField(
        upload_to="students/photos/",
        blank=True,
        null=True,
    )

    # School information
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name="students",
    )

    current_class = models.CharField(
        max_length=50,
    )

    section = models.CharField(
        max_length=10,
        blank=True,
    )

    roll_number = models.CharField(
        max_length=20,
        blank=True,
    )

    # Parent / Guardian
    parent_name = models.CharField(
        max_length=150,
    )

    parent_phone = models.CharField(
        max_length=15,
        blank=True,
    )

    parent_email = models.EmailField(
        blank=True,
    )

    relationship_to_student = models.CharField(
        max_length=50,
        default="Parent",
    )

    # Student contact
    student_phone = models.CharField(
        max_length=15,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    admission_date = models.DateField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.student_name} ({self.admission_number})"