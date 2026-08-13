from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from eligibility.models import EligibilityRecord
from .models import (
    InventoryItem,
    StockTransaction,
    Laptop,
    LaptopAssignment,
)


@transaction.atomic
def process_stock_in(
    item,
    quantity,
    source_destination="",
    reference_number="",
    performed_by="",
    notes="",
    unit_cost=None,
):
    """
    Process incoming inventory replenishment (Stock In).
    Atomically updates item stock and records transaction ledger.
    """
    if quantity <= 0:
        raise ValidationError("Stock In quantity must be greater than zero.")

    prev_stock = item.current_stock
    new_stock = prev_stock + quantity

    item.current_stock = new_stock
    if unit_cost is not None and unit_cost > 0:
        item.unit_cost = unit_cost
    item.save(update_fields=["current_stock", "unit_cost", "updated_at"] if (unit_cost is not None and unit_cost > 0) else ["current_stock", "updated_at"])

    transaction_record = StockTransaction.objects.create(
        item=item,
        transaction_type=StockTransaction.TransactionType.STOCK_IN,
        quantity=quantity,
        previous_stock=prev_stock,
        new_stock=new_stock,
        source_destination=source_destination,
        reference_number=reference_number,
        performed_by=performed_by,
        transaction_date=timezone.localdate(),
        notes=notes,
    )

    return transaction_record


@transaction.atomic
def process_stock_out(
    item,
    quantity,
    source_destination="",
    reference_number="",
    performed_by="",
    notes="",
):
    """
    Process outward inventory distribution/dispatch (Stock Out).
    Validates availability and atomically updates item stock and records transaction.
    """
    if quantity <= 0:
        raise ValidationError("Stock Out quantity must be greater than zero.")

    if item.current_stock < quantity:
        raise ValidationError(
            f"Insufficient stock for '{item.item_name}'. "
            f"Available: {item.current_stock} {item.unit}, Requested: {quantity} {item.unit}."
        )

    prev_stock = item.current_stock
    new_stock = prev_stock - quantity

    item.current_stock = new_stock
    item.save(update_fields=["current_stock", "updated_at"])

    transaction_record = StockTransaction.objects.create(
        item=item,
        transaction_type=StockTransaction.TransactionType.STOCK_OUT,
        quantity=quantity,
        previous_stock=prev_stock,
        new_stock=new_stock,
        source_destination=source_destination,
        reference_number=reference_number,
        performed_by=performed_by,
        transaction_date=timezone.localdate(),
        notes=notes,
    )

    return transaction_record


@transaction.atomic
def adjust_stock(
    item,
    new_quantity,
    reason="",
    performed_by="",
):
    """
    Manually reconcile or adjust inventory stock levels.
    """
    if new_quantity < 0:
        raise ValidationError("Stock level cannot be negative.")

    prev_stock = item.current_stock
    diff = new_quantity - prev_stock

    if diff == 0:
        return None

    item.current_stock = new_quantity
    item.save(update_fields=["current_stock", "updated_at"])

    transaction_record = StockTransaction.objects.create(
        item=item,
        transaction_type=StockTransaction.TransactionType.ADJUSTMENT,
        quantity=abs(diff),
        previous_stock=prev_stock,
        new_stock=new_quantity,
        source_destination="Manual Inventory Reconciliation",
        reference_number=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        performed_by=performed_by,
        transaction_date=timezone.localdate(),
        notes=f"Stock adjusted by {'+' if diff > 0 else ''}{diff}. Reason: {reason}",
    )

    return transaction_record


@transaction.atomic
def issue_laptop(student, laptop, academic_year, issue_notes="", bypass_eligibility=False):
    """Issue an available laptop to an eligible student."""

    if laptop.status != Laptop.Status.AVAILABLE:
        raise ValidationError(
            f"Laptop {laptop.asset_number} is not available."
        )

    if not bypass_eligibility:
        eligible = EligibilityRecord.objects.filter(
            student=student,
            benefit_type="LAPTOP",
            academic_year=academic_year,
            eligible=True,
        ).exists()

        # If eligibility records aren't populated yet, allow issuing
        if not eligible and EligibilityRecord.objects.filter(student=student, academic_year=academic_year).exists():
            raise ValidationError(
                f"{student.student_name} is not marked eligible for a laptop "
                f"for {academic_year}."
            )

    active_assignment = LaptopAssignment.objects.filter(
        student=student,
        status=LaptopAssignment.Status.ISSUED,
    ).exists()

    if active_assignment:
        raise ValidationError(
            f"{student.student_name} already has an active issued laptop."
        )

    assignment = LaptopAssignment.objects.create(
        laptop=laptop,
        student=student,
        academic_year=academic_year,
        status=LaptopAssignment.Status.ISSUED,
        issue_notes=issue_notes,
    )

    laptop.status = Laptop.Status.ISSUED
    laptop.save(update_fields=["status", "updated_at"])

    return assignment


@transaction.atomic
def return_laptop(assignment, return_notes="", condition="GOOD"):
    """Return an issued laptop and make it available again."""

    if assignment.status != LaptopAssignment.Status.ISSUED:
        raise ValidationError(
            "This laptop assignment is not currently active."
        )

    laptop = assignment.laptop

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
    if condition in [c[0] for c in Laptop.Condition.choices]:
        laptop.condition = condition
    laptop.save(update_fields=["status", "condition", "updated_at"])

    return assignment


@transaction.atomic
def replace_laptop(
    assignment,
    replacement_laptop,
    reason="",
):
    """Replace the laptop currently issued to a student."""

    if assignment.status != LaptopAssignment.Status.ISSUED:
        raise ValidationError(
            "Only an actively issued laptop can be replaced."
        )

    if replacement_laptop.status != Laptop.Status.AVAILABLE:
        raise ValidationError(
            f"Laptop {replacement_laptop.asset_number} "
            "is not available."
        )

    old_laptop = assignment.laptop

    # Mark old assignment as replaced
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

    # Mark old laptop as replaced/damaged
    old_laptop.status = Laptop.Status.DAMAGED
    old_laptop.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    # Create replacement assignment
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

    # Mark replacement laptop as issued
    replacement_laptop.status = Laptop.Status.ISSUED
    replacement_laptop.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return new_assignment
