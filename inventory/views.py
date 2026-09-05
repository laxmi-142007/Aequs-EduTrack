# inventory/views.py

import csv
import json
from decimal import Decimal

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import (
    InventoryItem,
    StockTransaction,
    Laptop,
    LaptopAssignment,
)

from .services import (
    process_stock_in,
    process_stock_out,
    issue_laptop,
    return_laptop,
    bulk_import_inventory,
)

from reports.models import log_activity


# =============================================================================
# HELPERS
# =============================================================================

def _current_user_name(request):
    if request.user.is_authenticated:
        return request.user.username
    return "Admin"


def _log(request, action, action_type="CREATE", object_type="", object_id="", details=""):
    """
    Central helper for Inventory activity logging.
    """

    log_activity(
        request,
        action=action,
        category="INVENTORY",
        action_type=action_type,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        details=details,
    )


def _item_to_dict(item):
    return {
        "id": item.id,
        "item_name": item.item_name,
        "sku": item.sku,
        "category": item.category,
        "category_display": item.get_category_display(),
        "unit": item.unit,
        "current_stock": item.current_stock,
        "low_stock_threshold": item.low_stock_threshold,
        "unit_cost": (
            float(item.unit_cost)
            if item.unit_cost is not None
            else 0
        ),
        "location": item.location,
        "description": item.description,
        "status": item.status,
        "status_display": item.get_status_display(),
        "stock_status": item.stock_status,
        "is_low_stock": item.is_low_stock,
        "created_at": (
            item.created_at.strftime("%Y-%m-%d %H:%M")
            if item.created_at
            else ""
        ),
        "updated_at": (
            item.updated_at.strftime("%Y-%m-%d %H:%M")
            if item.updated_at
            else ""
        ),
    }


def _transaction_to_dict(record):
    return {
        "id": record.id,
        "item_id": record.item_id,
        "item_name": record.item.item_name,
        "sku": record.item.sku,
        "transaction_type": record.transaction_type,
        "transaction_type_display": (
            record.get_transaction_type_display()
        ),
        "quantity": record.quantity,
        "previous_stock": record.previous_stock,
        "new_stock": record.new_stock,
        "source_destination": record.source_destination,
        "reference_number": record.reference_number,
        "performed_by": record.performed_by,
        "transaction_date": (
            record.transaction_date.strftime("%Y-%m-%d")
            if record.transaction_date
            else ""
        ),
        "notes": record.notes,
        "created_at": (
            record.created_at.strftime("%Y-%m-%d %H:%M")
            if record.created_at
            else ""
        ),
    }


def _laptop_to_dict(laptop):
    active_assignment = (
        laptop.assignments
        .filter(status=LaptopAssignment.Status.ISSUED)
        .select_related("student")
        .first()
    )

    return {
        "id": laptop.id,
        "asset_number": laptop.asset_number,
        "serial_number": laptop.serial_number,
        "brand": laptop.brand,
        "model_name": laptop.model_name,
        "purchase_date": (
            laptop.purchase_date.strftime("%Y-%m-%d")
            if laptop.purchase_date
            else ""
        ),
        "purchase_cost": (
            float(laptop.purchase_cost)
            if laptop.purchase_cost is not None
            else None
        ),
        "condition": laptop.condition,
        "condition_display": laptop.get_condition_display(),
        "status": laptop.status,
        "status_display": laptop.get_status_display(),
        "warranty_expiry": (
            laptop.warranty_expiry.strftime("%Y-%m-%d")
            if laptop.warranty_expiry
            else ""
        ),
        "notes": laptop.notes,
        "assigned": active_assignment is not None,
        "assigned_student": (
            active_assignment.student.student_name
            if active_assignment
            else ""
        ),
        "assignment_id": (
            active_assignment.id
            if active_assignment
            else None
        ),
    }


# =============================================================================
# INVENTORY PORTAL
# =============================================================================

@ensure_csrf_cookie
def inventory_portal(request):

    items = InventoryItem.objects.all()

    total_items = items.count()

    active_items = items.filter(
        status="ACTIVE"
    ).count()

    low_stock_count = sum(
        1
        for item in items
        if item.is_low_stock and item.current_stock > 0
    )

    out_of_stock_count = items.filter(
        current_stock=0
    ).count()

    total_stock = sum(
        item.current_stock
        for item in items
    )

    laptops = Laptop.objects.all()

    total_laptops = laptops.count()

    available_laptops = laptops.filter(
        status=Laptop.Status.AVAILABLE
    ).count()

    issued_laptops = laptops.filter(
        status=Laptop.Status.ISSUED
    ).count()

    context = {
        "items": items,
        "laptops": laptops,

        "total_items": total_items,
        "active_items": active_items,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_stock": total_stock,

        "total_laptops": total_laptops,
        "available_laptops": available_laptops,
        "issued_laptops": issued_laptops,

        "username": _current_user_name(request),
    }

    return render(
        request,
        "inventory/portal.html",
        context,
    )


# =============================================================================
# INVENTORY ITEMS API
# =============================================================================

@require_http_methods(["GET"])
def api_inventory_items(request):

    items = InventoryItem.objects.all()

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "").strip()
    status = request.GET.get("status", "").strip()

    if search:
        items = (
            items.filter(item_name__icontains=search)
            | items.filter(sku__icontains=search)
        )

    if category:
        items = items.filter(category=category)

    if status:
        items = items.filter(status=status)

    data = [
        _item_to_dict(item)
        for item in items
    ]

    return JsonResponse({
        "success": True,
        "items": data,
        "count": len(data),
    })


# =============================================================================
# CREATE INVENTORY ITEM
# =============================================================================

@require_http_methods(["POST"])
def api_create_inventory_item(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(
                request.body.decode("utf-8")
            )
        else:
            data = request.POST

        item_name = str(
            data.get("item_name")
            or data.get("itemName")
            or ""
        ).strip()

        sku = str(
            data.get("sku")
            or ""
        ).strip().upper()

        category = str(
            data.get("category")
            or "BOOKS"
        ).strip().upper()

        unit = str(
            data.get("unit")
            or "Pieces"
        ).strip()

        location = str(
            data.get("location")
            or ""
        ).strip()

        description = str(
            data.get("description")
            or ""
        ).strip()

        status = str(
            data.get("status")
            or "ACTIVE"
        ).strip().upper()

        if not item_name:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Item name is required.",
                },
                status=400,
            )

        if not sku:
            return JsonResponse(
                {
                    "success": False,
                    "error": "SKU is required.",
                },
                status=400,
            )

        if InventoryItem.objects.filter(
            sku=sku
        ).exists():
            return JsonResponse(
                {
                    "success": False,
                    "error": f"SKU '{sku}' already exists.",
                },
                status=400,
            )

        current_stock = int(
            data.get("current_stock")
            or data.get("currentStock")
            or 0
        )

        low_stock_threshold = int(
            data.get("low_stock_threshold")
            or data.get("lowStockThreshold")
            or 10
        )

        unit_cost_value = (
            data.get("unit_cost")
            or data.get("unitCost")
            or "0"
        )

        unit_cost = Decimal(
            str(unit_cost_value)
        )

        if current_stock < 0:
            raise ValueError(
                "Current stock cannot be negative."
            )

        if low_stock_threshold < 0:
            raise ValueError(
                "Low stock threshold cannot be negative."
            )

        if unit_cost < 0:
            raise ValueError(
                "Unit cost cannot be negative."
            )

        item = InventoryItem.objects.create(
            item_name=item_name,
            sku=sku,
            category=category,
            unit=unit,
            current_stock=current_stock,
            low_stock_threshold=low_stock_threshold,
            unit_cost=unit_cost,
            location=location,
            description=description,
            status=status,
        )

        # LOG CREATE
        _log(
            request,
            action=f"Created inventory item '{item.item_name}'",
            action_type="CREATE",
            object_type="InventoryItem",
            object_id=item.id,
            details=(
                f"SKU: {item.sku}; "
                f"Category: {item.category}; "
                f"Initial stock: {item.current_stock}"
            ),
        )

        return JsonResponse({
            "success": True,
            "message": "Inventory item created successfully.",
            "item": _item_to_dict(item),
        })

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )


# =============================================================================
# UPDATE INVENTORY ITEM
# =============================================================================

@require_http_methods(["POST", "PUT"])
def api_update_inventory_item(request, item_id):

    try:

        item = get_object_or_404(
            InventoryItem,
            id=item_id,
        )

        old_values = {
            "item_name": item.item_name,
            "sku": item.sku,
            "category": item.category,
            "unit": item.unit,
            "low_stock_threshold": item.low_stock_threshold,
            "unit_cost": str(item.unit_cost),
            "location": item.location,
            "description": item.description,
            "status": item.status,
        }

        if request.content_type == "application/json":
            data = json.loads(
                request.body.decode("utf-8")
            )
        else:
            data = request.POST

        if "item_name" in data:
            item.item_name = str(
                data["item_name"]
            ).strip()

        if "sku" in data:

            new_sku = str(
                data["sku"]
            ).strip().upper()

            if InventoryItem.objects.filter(
                sku=new_sku
            ).exclude(
                id=item.id
            ).exists():

                return JsonResponse(
                    {
                        "success": False,
                        "error": f"SKU '{new_sku}' already exists.",
                    },
                    status=400,
                )

            item.sku = new_sku

        if "category" in data:
            item.category = str(
                data["category"]
            ).strip().upper()

        if "unit" in data:
            item.unit = str(
                data["unit"]
            ).strip()

        if "low_stock_threshold" in data:
            item.low_stock_threshold = int(
                data["low_stock_threshold"]
            )

        if "unit_cost" in data:
            item.unit_cost = Decimal(
                str(data["unit_cost"] or "0")
            )

        if "location" in data:
            item.location = str(
                data["location"]
            ).strip()

        if "description" in data:
            item.description = str(
                data["description"]
            ).strip()

        if "status" in data:
            item.status = str(
                data["status"]
            ).strip().upper()

        item.save()

        new_values = {
            "item_name": item.item_name,
            "sku": item.sku,
            "category": item.category,
            "unit": item.unit,
            "low_stock_threshold": item.low_stock_threshold,
            "unit_cost": str(item.unit_cost),
            "location": item.location,
            "description": item.description,
            "status": item.status,
        }

        changes = []

        for field in old_values:

            if old_values[field] != new_values[field]:

                changes.append(
                    f"{field}: "
                    f"'{old_values[field]}' → "
                    f"'{new_values[field]}'"
                )

        # LOG UPDATE
        _log(
            request,
            action=f"Updated inventory item '{item.item_name}'",
            action_type="UPDATE",
            object_type="InventoryItem",
            object_id=item.id,
            details=(
                "; ".join(changes)
                if changes
                else "Item opened and saved without field changes."
            ),
        )

        return JsonResponse({
            "success": True,
            "message": "Inventory item updated successfully.",
            "item": _item_to_dict(item),
        })

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )


# =============================================================================
# DELETE INVENTORY ITEM
# =============================================================================

@require_http_methods(["POST", "DELETE"])
def api_delete_inventory_item(request, item_id):

    try:

        item = get_object_or_404(
            InventoryItem,
            id=item_id,
        )

        # Save values BEFORE deleting.
        deleted_item_name = item.item_name
        deleted_sku = item.sku
        deleted_category = item.category
        deleted_stock = item.current_stock

        # DELETE FIRST
        item.delete()

        # LOG AFTER DELETE
        # We use the saved values because the object no longer exists.
        _log(
            request,
            action=f"Deleted inventory item '{deleted_item_name}'",
            action_type="DELETE",
            object_type="InventoryItem",
            object_id=item_id,
            details=(
                f"SKU: {deleted_sku}; "
                f"Category: {deleted_category}; "
                f"Stock at deletion: {deleted_stock}"
            ),
        )

        return JsonResponse({
            "success": True,
            "message": "Inventory item deleted successfully.",
        })

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )


# =============================================================================
# STOCK IN
# =============================================================================

@require_http_methods(["POST"])
def api_stock_in(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(
                request.body.decode("utf-8")
            )
        else:
            data = request.POST

        item_id = (
            data.get("item_id")
            or data.get("itemId")
        )

        quantity = int(
            data.get("quantity")
            or 0
        )

        item = get_object_or_404(
            InventoryItem,
            id=item_id,
        )

        record = process_stock_in(
            item=item,
            quantity=quantity,
            source_destination=str(
                data.get("source_destination")
                or data.get("sourceDestination")
                or ""
            ).strip(),
            reference_number=str(
                data.get("reference_number")
                or data.get("referenceNumber")
                or ""
            ).strip(),
            performed_by=_current_user_name(request),
            notes=str(
                data.get("notes")
                or ""
            ).strip(),
            unit_cost=(
                Decimal(
                    str(data["unit_cost"])
                )
                if data.get("unit_cost")
                else None
            ),
        )

        _log(
            request,
            action=f"Added stock for '{item.item_name}'",
            action_type="STOCK_IN",
            object_type="InventoryItem",
            object_id=item.id,
            details=(
                f"Quantity: {quantity}; "
                f"New stock: {item.current_stock}; "
                f"Transaction ID: {record.id}"
            ),
        )

        return JsonResponse({
            "success": True,
            "message": "Stock added successfully.",
            "transaction": _transaction_to_dict(record),
            "item": _item_to_dict(item),
        })

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )


# =============================================================================
# STOCK OUT
# =============================================================================

@require_http_methods(["POST"])
def api_stock_out(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(
                request.body.decode("utf-8")
            )
        else:
            data = request.POST

        item_id = (
            data.get("item_id")
            or data.get("itemId")
        )

        quantity = int(
            data.get("quantity")
            or 0
        )

        item = get_object_or_404(
            InventoryItem,
            id=item_id,
        )

        record = process_stock_out(
            item=item,
            quantity=quantity,
            source_destination=str(
                data.get("source_destination")
                or data.get("sourceDestination")
                or ""
            ).strip(),
            reference_number=str(
                data.get("reference_number")
                or data.get("referenceNumber")
                or ""
            ).strip(),
            performed_by=_current_user_name(request),
            notes=str(
                data.get("notes")
                or ""
            ).strip(),
        )

        _log(
            request,
            action=f"Removed stock from '{item.item_name}'",
            action_type="STOCK_OUT",
            object_type="InventoryItem",
            object_id=item.id,
            details=(
                f"Quantity: {quantity}; "
                f"New stock: {item.current_stock}; "
                f"Transaction ID: {record.id}"
            ),
        )

        return JsonResponse({
            "success": True,
            "message": "Stock removed successfully.",
            "transaction": _transaction_to_dict(record),
            "item": _item_to_dict(item),
        })

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )


# =============================================================================
# TRANSACTIONS
# =============================================================================

@require_http_methods(["GET"])
def api_stock_transactions(request):

    transactions = (
        StockTransaction.objects
        .select_related("item")
        .all()
    )

    item_id = request.GET.get("item_id")

    transaction_type = request.GET.get(
        "transaction_type"
    )

    if item_id:
        transactions = transactions.filter(
            item_id=item_id
        )

    if transaction_type:
        transactions = transactions.filter(
            transaction_type=transaction_type
        )

    data = [
        _transaction_to_dict(record)
        for record in transactions
    ]

    return JsonResponse({
        "success": True,
        "transactions": data,
        "count": len(data),
    })


# =============================================================================
# LOW STOCK ALERTS
# =============================================================================

@require_http_methods(["GET"])
def api_low_stock_alerts(request):

    items = InventoryItem.objects.filter(
        status="ACTIVE"
    )

    low_stock_items = [
        item
        for item in items
        if item.is_low_stock
    ]

    data = [
        _item_to_dict(item)
        for item in low_stock_items
    ]

    return JsonResponse({
        "success": True,
        "alerts": data,
        "count": len(data),
    })


# =============================================================================
# LAPTOPS
# =============================================================================

@require_http_methods(["GET"])
def api_laptops(request):

    laptops = Laptop.objects.all()

    status = request.GET.get("status")
    search = request.GET.get("search", "").strip()

    if status:
        laptops = laptops.filter(
            status=status
        )

    if search:
        laptops = (
            laptops.filter(
                asset_number__icontains=search
            )
            | laptops.filter(
                serial_number__icontains=search
            )
            | laptops.filter(
                brand__icontains=search
            )
            | laptops.filter(
                model_name__icontains=search
            )
        )

    data = [
        _laptop_to_dict(laptop)
        for laptop in laptops
    ]

    return JsonResponse({
        "success": True,
        "laptops": data,
        "count": len(data),
    })


# =============================================================================
# CREATE LAPTOP
# =============================================================================

@require_http_methods(["POST"])
def api_create_laptop(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(
                request.body.decode("utf-8")
            )
        else:
            data = request.POST

        asset_number = str(
            data.get("asset_number")
            or data.get("assetNumber")
            or ""
        ).strip()

        serial_number = str(
            data.get("serial_number")
            or data.get("serialNumber")
            or ""
        ).strip()

        brand = str(
            data.get("brand")
            or ""
        ).strip()

        model_name = str(
            data.get("model_name")
            or data.get("modelName")
            or ""
        ).strip()

        if not asset_number:
            raise ValueError(
                "Asset number is required."
            )

        if not serial_number:
            raise ValueError(
                "Serial number is required."
            )

        if not brand:
            raise ValueError(
                "Brand is required."
            )

        if not model_name:
            raise ValueError(
                "Model name is required."
            )

        if Laptop.objects.filter(
            asset_number=asset_number
        ).exists():
            raise ValueError(
                "Asset number already exists."
            )

        if Laptop.objects.filter(
            serial_number=serial_number
        ).exists():
            raise ValueError(
                "Serial number already exists."
            )

        laptop = Laptop.objects.create(
            asset_number=asset_number,
            serial_number=serial_number,
            brand=brand,
            model_name=model_name,
            condition=str(
                data.get("condition")
                or Laptop.Condition.NEW
            ).upper(),
            status=str(
                data.get("status")
                or Laptop.Status.AVAILABLE
            ).upper(),
            notes=str(
                data.get("notes")
                or ""
            ).strip(),
        )

        _log(
            request,
            action=f"Created laptop '{laptop.asset_number}'",
            action_type="CREATE",
            object_type="Laptop",
            object_id=laptop.id,
            details=(
                f"Serial number: {laptop.serial_number}; "
                f"Brand: {laptop.brand}; "
                f"Model: {laptop.model_name}"
            ),
        )

        return JsonResponse({
            "success": True,
            "message": "Laptop created successfully.",
            "laptop": _laptop_to_dict(laptop),
        })

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )


# =============================================================================
# ISSUE LAPTOP
# =============================================================================

@require_http_methods(["POST"])
def api_issue_laptop(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(
                request.body.decode("utf-8")
            )
        else:
            data = request.POST

        laptop_id = (
            data.get("laptop_id")
            or data.get("laptopId")
        )

        student_id = (
            data.get("student_id")
            or data.get("studentId")
        )

        academic_year = str(
            data.get("academic_year")
            or data.get("academicYear")
            or ""
        ).strip()

        laptop = get_object_or_404(
            Laptop,
            id=laptop_id,
        )

        from students.models import Student

        student = get_object_or_404(
            Student,
            id=student_id,
        )

        assignment = issue_laptop(
            student=student,
            laptop=laptop,
            academic_year=academic_year,
            issue_notes=str(
                data.get("issue_notes")
                or data.get("issueNotes")
                or ""
            ).strip(),
            bypass_eligibility=(
                str(
                    data.get("bypass_eligibility")
                    or ""
                ).lower()
                in {"1", "true", "yes"}
            ),
        )

        _log(
            request,
            action=f"Issued laptop '{laptop.asset_number}'",
            action_type="ISSUE",
            object_type="Laptop",
            object_id=laptop.id,
            details=(
                f"Student: {student.student_name}; "
                f"Student ID: {student.id}; "
                f"Assignment ID: {assignment.id}; "
                f"Academic year: {academic_year}"
            ),
        )

        return JsonResponse({
            "success": True,
            "message": "Laptop issued successfully.",
            "assignment_id": assignment.id,
        })

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )


# =============================================================================
# RETURN LAPTOP
# =============================================================================

@require_http_methods(["POST"])
def api_return_laptop(request, laptop_id):

    try:

        laptop = get_object_or_404(
            Laptop,
            id=laptop_id,
        )

        assignment = (
            LaptopAssignment.objects
            .filter(
                laptop=laptop,
                status=LaptopAssignment.Status.ISSUED,
            )
            .select_related("student")
            .order_by("-created_at")
            .first()
        )

        if not assignment:
            raise ValueError(
                "No active assignment found for this laptop."
            )

        if request.content_type == "application/json":
            data = json.loads(
                request.body.decode("utf-8")
            )
        else:
            data = request.POST

        result = return_laptop(
            assignment=assignment,
            return_notes=str(
                data.get("return_notes")
                or data.get("returnNotes")
                or ""
            ).strip(),
            condition=str(
                data.get("condition")
                or Laptop.Condition.GOOD
            ).upper(),
        )

        _log(
            request,
            action=f"Returned laptop '{laptop.asset_number}'",
            action_type="RETURN",
            object_type="Laptop",
            object_id=laptop.id,
            details=(
                f"Student: {assignment.student.student_name}; "
                f"Assignment ID: {result.id}"
            ),
        )

        return JsonResponse({
            "success": True,
            "message": "Laptop returned successfully.",
            "assignment_id": result.id,
            "laptop": _laptop_to_dict(laptop),
        })

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )


# =============================================================================
# INVENTORY CSV TEMPLATE
# =============================================================================

@require_http_methods(["GET"])
def inventory_csv_template(request):

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; '
        'filename="inventory_bulk_upload_template.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "item_name",
        "sku",
        "category",
        "current_stock",
        "unit",
        "low_stock_threshold",
        "unit_cost",
        "location",
        "description",
        "status",
    ])

    writer.writerow([
        "Mathematics Textbook",
        "BOOK-001",
        "BOOKS",
        "100",
        "Pieces",
        "10",
        "250.00",
        "Warehouse A",
        "Class 10 Mathematics textbook",
        "ACTIVE",
    ])

    writer.writerow([
        "Student Workbook",
        "WORK-001",
        "WORKBOOKS",
        "200",
        "Pieces",
        "20",
        "120.00",
        "Warehouse A",
        "Student practice workbook",
        "ACTIVE",
    ])

    return response


# =============================================================================
# INVENTORY BULK UPLOAD
# =============================================================================

@require_http_methods(["GET", "POST"])
def inventory_bulk_upload(request):

    if request.method == "GET":
        return render(
            request,
            "inventory/bulk_upload.html"
        )

    uploaded_file = request.FILES.get("file")

    if not uploaded_file:
        messages.error(
            request,
            "Please select a CSV or Excel file."
        )
        return redirect("inventory:bulk_upload")

    filename = uploaded_file.name.lower()

    if not filename.endswith(
        (".csv", ".xlsx")
    ):
        messages.error(
            request,
            "Invalid file format. Please upload CSV or XLSX."
        )
        return redirect("inventory:bulk_upload")

    try:

        result = bulk_import_inventory(
            file_obj=uploaded_file,
            filename=uploaded_file.name,
            performed_by=(
                request.user.username
                if request.user.is_authenticated
                else "Admin"
            ),
        )

        created = result.get("created", 0)
        updated = result.get("updated", 0)

        _log(
            request,
            action="Bulk inventory upload completed",
            action_type="IMPORT",
            object_type="Inventory",
            details=(
                f"File: {uploaded_file.name}; "
                f"Created: {created}; "
                f"Updated: {updated}"
            ),
        )

        messages.success(
            request,
            f"Inventory upload successful! "
            f"Created: {created}, Updated: {updated}."
        )

    except Exception as exc:

        _log(
            request,
            action="Bulk inventory upload failed",
            action_type="ERROR",
            object_type="Inventory",
            details=(
                f"File: {uploaded_file.name}; "
                f"Error: {str(exc)}"
            ),
        )

        messages.error(
            request,
            f"Inventory upload failed: {exc}"
        )

    return redirect("inventory:bulk_upload")


# =============================================================================
# EXPORT INVENTORY CSV
# =============================================================================

@require_http_methods(["GET"])
def api_export_csv(request):

    items = InventoryItem.objects.all()

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; filename="inventory_export.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
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
    ])

    for item in items:

        writer.writerow([
            item.item_name,
            item.sku,
            item.category,
            item.unit,
            item.current_stock,
            item.low_stock_threshold,
            item.unit_cost,
            item.location,
            item.description,
            item.status,
        ])

    _log(
        request,
        action="Exported inventory CSV",
        action_type="EXPORT",
        object_type="Inventory",
        details=f"Exported {items.count()} inventory items.",
    )

    return response
