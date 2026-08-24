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

    # Mark old laptop as replaced/damaged
    old_laptop.status = Laptop.Status.DAMAGED
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

# =============================================================================
# BULK INVENTORY IMPORT
# =============================================================================

import csv
import io
from decimal import Decimal, InvalidOperation


INVENTORY_IMPORT_COLUMNS = [
    "item_name",
    "sku",
    "category",
    "unit",
    "current_stock",
    "low_stock_threshold",
    "unit_cost",
    "location",
    "description",
    "status",
]


def _bulk_clean_value(value):
    if value is None:
        return ""
    return str(value).strip()


def _bulk_parse_non_negative_int(value, field_name, row_number):
    value = _bulk_clean_value(value)

    if value == "":
        return 0

    try:
        number = int(float(value))
    except (ValueError, TypeError):
        raise ValidationError(
            f"Row {row_number}: {field_name} must be a whole number."
        )

    if number < 0:
        raise ValidationError(
            f"Row {row_number}: {field_name} cannot be negative."
        )

    return number


def _bulk_parse_decimal(value, field_name, row_number):
    value = _bulk_clean_value(value)

    if value == "":
        return Decimal("0.00")

    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(
            f"Row {row_number}: {field_name} must be a valid number."
        )

    if number < 0:
        raise ValidationError(
            f"Row {row_number}: {field_name} cannot be negative."
        )

    return number


def _bulk_validate_row(row, row_number, existing_skus, uploaded_skus):

    item_name = _bulk_clean_value(row.get("item_name"))
    sku = _bulk_clean_value(row.get("sku")).upper()
    category = _bulk_clean_value(row.get("category")).upper()
    unit = _bulk_clean_value(row.get("unit")) or "Pieces"
    location = _bulk_clean_value(row.get("location"))
    description = _bulk_clean_value(row.get("description"))
    status = _bulk_clean_value(row.get("status")).upper() or "ACTIVE"

    if not item_name:
        raise ValidationError(
            f"Row {row_number}: item_name is required."
        )

    if not sku:
        raise ValidationError(
            f"Row {row_number}: sku is required."
        )

    if sku in existing_skus:
        raise ValidationError(
            f"Row {row_number}: SKU '{sku}' already exists in the database."
        )

    if sku in uploaded_skus:
        raise ValidationError(
            f"Row {row_number}: duplicate SKU '{sku}' in uploaded file."
        )

    valid_categories = {
        choice[0] for choice in InventoryCategory.choices
    }

    if category not in valid_categories:
        raise ValidationError(
            f"Row {row_number}: invalid category '{category}'. "
            f"Allowed values: {', '.join(sorted(valid_categories))}."
        )

    if status not in {"ACTIVE", "INACTIVE"}:
        raise ValidationError(
            f"Row {row_number}: invalid status '{status}'. "
            f"Allowed values: ACTIVE, INACTIVE."
        )

    current_stock = _bulk_parse_non_negative_int(
        row.get("current_stock"),
        "current_stock",
        row_number,
    )

    low_stock_threshold = _bulk_parse_non_negative_int(
        row.get("low_stock_threshold"),
        "low_stock_threshold",
        row_number,
    )

    unit_cost = _bulk_parse_decimal(
        row.get("unit_cost"),
        "unit_cost",
        row_number,
    )

    return {
        "item_name": item_name,
        "sku": sku,
        "category": category,
        "unit": unit,
        "current_stock": current_stock,
        "low_stock_threshold": low_stock_threshold,
        "unit_cost": unit_cost,
        "location": location,
        "description": description,
        "status": status,
    }


def _bulk_read_csv(file_obj):

    raw_data = file_obj.read()

    if isinstance(raw_data, bytes):
        try:
            raw_data = raw_data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raw_data = raw_data.decode("cp1252")

    reader = csv.DictReader(io.StringIO(raw_data))

    if not reader.fieldnames:
        raise ValidationError("The CSV file is empty.")

    headers = [
        str(header).strip()
        for header in reader.fieldnames
        if header is not None
    ]

    missing_columns = [
        column
        for column in INVENTORY_IMPORT_COLUMNS
        if column not in headers
    ]

    if missing_columns:
        raise ValidationError(
            "Missing required columns: " +
            ", ".join(missing_columns)
        )

    rows = []

    for row in reader:

        cleaned_row = {
            str(key).strip(): value
            for key, value in row.items()
            if key is not None
        }

        if not any(
            _bulk_clean_value(value)
            for value in cleaned_row.values()
        ):
            continue

        rows.append(cleaned_row)

    return rows


def _bulk_read_excel(file_obj):

    try:
        import openpyxl
    except ImportError:
        raise ValidationError(
            "Excel support requires openpyxl. "
            "Run: python -m pip install openpyxl"
        )

    try:
        workbook = openpyxl.load_workbook(
            file_obj,
            read_only=True,
            data_only=True,
        )
    except Exception as exc:
        raise ValidationError(
            f"Unable to read Excel file: {exc}"
        )

    worksheet = workbook.active

    rows_iterator = worksheet.iter_rows(values_only=True)

    try:
        header_row = next(rows_iterator)
    except StopIteration:
        workbook.close()
        raise ValidationError("The Excel file is empty.")

    headers = [
        _bulk_clean_value(value)
        for value in header_row
    ]

    missing_columns = [
        column
        for column in INVENTORY_IMPORT_COLUMNS
        if column not in headers
    ]

    if missing_columns:
        workbook.close()
        raise ValidationError(
            "Missing required columns: " +
            ", ".join(missing_columns)
        )

    rows = []

    for values in rows_iterator:

        row = {}

        for index, header in enumerate(headers):

            if not header:
                continue

            value = (
                values[index]
                if index < len(values)
                else ""
            )

            row[header] = value

        if not any(
            _bulk_clean_value(value)
            for value in row.values()
        ):
            continue

        rows.append(row)

    workbook.close()

    return rows


@transaction.atomic
def bulk_import_inventory(
    file_obj,
    filename,
    performed_by="",
):

    filename_lower = filename.lower()

    if filename_lower.endswith(".csv"):

        rows = _bulk_read_csv(file_obj)

    elif filename_lower.endswith(".xlsx"):

        rows = _bulk_read_excel(file_obj)

    else:

        raise ValidationError(
            "Unsupported file format. "
            "Please upload a CSV or XLSX file."
        )

    if not rows:
        raise ValidationError(
            "The uploaded file does not contain "
            "any inventory records."
        )

    existing_skus = set(
        InventoryItem.objects.values_list(
            "sku",
            flat=True,
        )
    )

    existing_skus = {
        str(sku).strip().upper()
        for sku in existing_skus
    }

    uploaded_skus = set()
    validated_rows = []

    for row_number, row in enumerate(
        rows,
        start=2,
    ):

        validated = _bulk_validate_row(
            row,
            row_number,
            existing_skus,
            uploaded_skus,
        )

        uploaded_skus.add(validated["sku"])

        validated_rows.append(validated)

    created_items = []

    import_reference = (
        f"IMPORT-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    )

    for data in validated_rows:

        opening_stock = data["current_stock"]

        item = InventoryItem.objects.create(
            item_name=data["item_name"],
            sku=data["sku"],
            category=data["category"],
            unit=data["unit"],
            current_stock=0,
            low_stock_threshold=data["low_stock_threshold"],
            unit_cost=data["unit_cost"],
            location=data["location"],
            description=data["description"],
            status=data["status"],
        )

        if opening_stock > 0:

            process_stock_in(
                item=item,
                quantity=opening_stock,
                source_destination="Bulk Inventory Import",
                reference_number=import_reference,
                performed_by=performed_by,
                notes=(
                    f"Opening stock imported from "
                    f"{filename}"
                ),
            )

        created_items.append(item)

    return {
        "created": len(created_items),
        "items": created_items,
    }

