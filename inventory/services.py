from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from eligibility.models import EligibilityRecord
from .models import Laptop, LaptopAssignment


@transaction.atomic
def issue_laptop(student, laptop, academic_year):
    """Issue an available laptop to an eligible student."""

    laptop = Laptop.objects.select_for_update().get(
        pk=laptop.pk
    )

    if laptop.status != Laptop.Status.AVAILABLE:
        raise ValidationError(
            f"Laptop {laptop.asset_number} is not available."
        )

    eligible = EligibilityRecord.objects.filter(
        student=student,
        benefit_type="LAPTOP",
        academic_year=academic_year,
        eligible=True,
    ).exists()

    if not eligible:
        raise ValidationError(
            f"{student.student_name} is not eligible for a laptop "
            f"for {academic_year}."
        )

    active_assignment = LaptopAssignment.objects.filter(
        student=student,
        status=LaptopAssignment.Status.ISSUED,
    ).exists()

    if active_assignment:
        raise ValidationError(
            f"{student.student_name} already has an issued laptop."
        )

    assignment = LaptopAssignment.objects.create(
        laptop=laptop,
        student=student,
        academic_year=academic_year,
        status=LaptopAssignment.Status.ISSUED,
    )

    laptop.status = Laptop.Status.ISSUED
    laptop.save(update_fields=["status", "updated_at"])

    return assignment


@transaction.atomic
def return_laptop(assignment, return_notes=""):
    """Return an issued laptop and make it available again."""

    assignment = (
        LaptopAssignment.objects
        .select_for_update()
        .select_related("laptop")
        .get(pk=assignment.pk)
    )

    if assignment.status != LaptopAssignment.Status.ISSUED:
        raise ValidationError(
            "This laptop assignment is not currently active."
        )

    laptop = Laptop.objects.select_for_update().get(
        pk=assignment.laptop_id
    )

    assignment.status = LaptopAssignment.Status.RETURNED
    assignment.returned_date = timezone.localdate()
    assignment.return_notes = return_notes

    assignment.save(
        update_fields=[
            "status",
            "returned_date",
            "return_notes",
            "updated_at",
        ]
    )

    laptop.status = Laptop.Status.AVAILABLE
    laptop.save(update_fields=["status", "updated_at"])

    return assignment


@transaction.atomic
def replace_laptop(
    assignment,
    replacement_laptop,
    reason="",
):
    """Replace the laptop currently issued to a student."""

    assignment = (
        LaptopAssignment.objects
        .select_for_update()
        .select_related("laptop")
        .get(pk=assignment.pk)
    )

    replacement_laptop = Laptop.objects.select_for_update().get(
        pk=replacement_laptop.pk
    )

    if assignment.status != LaptopAssignment.Status.ISSUED:
        raise ValidationError(
            "Only an actively issued laptop can be replaced."
        )

    if replacement_laptop.status != Laptop.Status.AVAILABLE:
        raise ValidationError(
            f"Laptop {replacement_laptop.asset_number} "
            "is not available."
        )

    old_laptop = Laptop.objects.select_for_update().get(
        pk=assignment.laptop_id
    )

    assignment.status = LaptopAssignment.Status.REPLACED
    assignment.returned_date = timezone.localdate()
    assignment.return_notes = reason

    assignment.save(
        update_fields=[
            "status",
            "returned_date",
            "return_notes",
            "updated_at",
        ]
    )

    # Old physical laptop is now available again.
    old_laptop.status = Laptop.Status.REPLACED

    old_laptop.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    new_assignment = LaptopAssignment.objects.create(
        laptop=replacement_laptop,
        student=assignment.student,
        academic_year=assignment.academic_year,
        status=LaptopAssignment.Status.ISSUED,
        issue_notes=(
            f"Replacement for {old_laptop.asset_number}. "
            f"Reason: {reason}"
        ),
    )

    replacement_laptop.status = Laptop.Status.ISSUED

    replacement_laptop.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return new_assignment
