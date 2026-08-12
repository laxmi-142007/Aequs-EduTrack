from django.db import models


class School(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    name = models.CharField(max_length=200)

    udise_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Government school UDISE code",
    )

    address = models.TextField()

    district = models.CharField(max_length=100)

    taluk = models.CharField(
        max_length=100,
        blank=True,
    )

    village = models.CharField(
        max_length=100,
        blank=True,
    )

    pincode = models.CharField(
        max_length=10,
        blank=True,
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    headmaster_name = models.CharField(
        max_length=150,
    )

    headmaster_phone = models.CharField(
        max_length=15,
        blank=True,
    )

    student_strength = models.PositiveIntegerField(
        default=0,
    )

    established_year = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.name} ({self.udise_code})"