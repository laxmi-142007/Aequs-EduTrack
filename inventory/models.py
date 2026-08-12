from django.db import models


class Laptop(models.Model):

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ISSUED = "ISSUED", "Issued"
        RETURNED = "RETURNED", "Returned"
        DAMAGED = "DAMAGED", "Damaged"
        LOST = "LOST", "Lost"
        RETIRED = "RETIRED", "Retired"

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"
        DAMAGED = "DAMAGED", "Damaged"

    asset_number = models.CharField(
        max_length=50,
        unique=True
    )

    serial_number = models.CharField(
        max_length=100,
        unique=True
    )

    brand = models.CharField(
        max_length=100
    )

    model_name = models.CharField(
        max_length=100
    )

    purchase_date = models.DateField(
        null=True,
        blank=True
    )

    purchase_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.NEW
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )

    warranty_expiry = models.DateField(
        null=True,
        blank=True
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.asset_number} - {self.serial_number}"


class LaptopAssignment(models.Model):

    class Status(models.TextChoices):
        ISSUED = "ISSUED", "Issued"
        RETURNED = "RETURNED", "Returned"
        REPLACED = "REPLACED", "Replaced"

    laptop = models.ForeignKey(
        Laptop,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="laptop_assignments",
    )

    academic_year = models.CharField(
        max_length=20
    )

    issued_date = models.DateField(
        auto_now_add=True
    )

    returned_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ISSUED
    )

    issue_notes = models.TextField(
        blank=True
    )

    return_notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.student.student_name} - "
            f"{self.laptop.asset_number}"
        )
