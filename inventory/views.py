import csv
import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q, Count

from .models import (
    InventoryCategory,
    InventoryItem,
    StockTransaction,
    Laptop,
    LaptopAssignment,
)
from .services import (
    process_stock_in,
    process_stock_out,
    adjust_stock,
    issue_laptop,
    return_laptop,
    replace_laptop,
)
from students.models import Student
from schools.models import School


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
        "unit_cost": float(item.unit_cost) if item.unit_cost is not None else 0.0,
        "location": item.location or "",
        "description": item.description or "",
        "status": item.status,
        "is_low_stock": item.is_low_stock,
        "stock_status": item.stock_status,
        "created_at": item.created_at.strftime("%Y-%m-%d"),
        "updated_at": item.updated_at.strftime("%Y-%m-%d %H:%M"),
    }


def _transaction_to_dict(tx):
    return {
        "id": tx.id,
        "item_id": tx.item.id,
        "item_name": tx.item.item_name,
        "item_sku": tx.item.sku,
        "item_unit": tx.item.unit,
        "category_display": tx.item.get_category_display(),
        "transaction_type": tx.transaction_type,
        "transaction_type_display": tx.get_transaction_type_display(),
        "quantity": tx.quantity,
        "previous_stock": tx.previous_stock,
        "new_stock": tx.new_stock,
        "source_destination": tx.source_destination or "N/A",
        "reference_number": tx.reference_number or "N/A",
        "performed_by": tx.performed_by or "System Admin",
        "transaction_date": tx.transaction_date.strftime("%Y-%m-%d"),
        "notes": tx.notes or "",
        "created_at": tx.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def _laptop_to_dict(laptop):
    active_assign = laptop.assignments.filter(status=LaptopAssignment.Status.ISSUED).first()
    return {
        "id": laptop.id,
        "asset_number": laptop.asset_number,
        "serial_number": laptop.serial_number,
        "brand": laptop.brand,
        "model_name": laptop.model_name,
        "purchase_date": laptop.purchase_date.strftime("%Y-%m-%d") if laptop.purchase_date else "",
        "purchase_cost": float(laptop.purchase_cost) if laptop.purchase_cost else 0.0,
        "condition": laptop.condition,
        "condition_display": laptop.get_condition_display(),
        "status": laptop.status,
        "status_display": laptop.get_status_display(),
        "warranty_expiry": laptop.warranty_expiry.strftime("%Y-%m-%d") if laptop.warranty_expiry else "",
        "notes": laptop.notes or "",
        "current_assignment": {
            "assignment_id": active_assign.id,
            "student_id": active_assign.student.id,
            "student_name": active_assign.student.student_name,
            "admission_number": active_assign.student.admission_number,
            "academic_year": active_assign.academic_year,
            "issued_date": active_assign.issued_date.strftime("%Y-%m-%d"),
        } if active_assign else None,
    }


def _ensure_initial_inventory_data():
    """Seed comprehensive demo data if database is empty"""
    if InventoryItem.objects.exists():
        return

    # Seed sample items
    items_data = [
        # 1. Books
        {
            "name": "Class 10 NCERT Mathematics",
            "sku": "BK-NCERT-M10",
            "category": InventoryCategory.BOOKS,
            "unit": "Copies",
            "stock": 120,
            "threshold": 25,
            "cost": 150.00,
            "location": "Warehouse A - Rack B1",
            "desc": "Standard Class 10 State Syllabus Mathematics Textbook",
        },
        {
            "name": "Class 8 Science & Environmental Studies",
            "sku": "BK-SCI-08",
            "category": InventoryCategory.BOOKS,
            "unit": "Copies",
            "stock": 8,
            "threshold": 20,
            "cost": 140.00,
            "location": "Warehouse A - Rack B2",
            "desc": "General Science textbook with experiment guides",
        },
        {
            "name": "English Grammar & Reader - Class 6",
            "sku": "BK-ENG-06",
            "category": InventoryCategory.BOOKS,
            "unit": "Copies",
            "stock": 0,
            "threshold": 15,
            "cost": 110.00,
            "location": "Warehouse A - Rack B3",
            "desc": "Foundation English literature & workbook",
        },

        # 2. Workbooks
        {
            "name": "STEM Practical Science Workbook",
            "sku": "WB-STEM-09",
            "category": InventoryCategory.WORKBOOKS,
            "unit": "Workbooks",
            "stock": 85,
            "threshold": 15,
            "cost": 85.00,
            "location": "Warehouse A - Rack W1",
            "desc": "Hands-on physics and chemistry activity workbook",
        },
        {
            "name": "Mathematics Problem Solving Workbook",
            "sku": "WB-MATH-07",
            "category": InventoryCategory.WORKBOOKS,
            "unit": "Workbooks",
            "stock": 14,
            "threshold": 20,
            "cost": 75.00,
            "location": "Warehouse A - Rack W2",
            "desc": "Daily math practice exercises workbook",
        },

        # 3. Study Kits
        {
            "name": "Aequs Comprehensive Student Study Kit",
            "sku": "SK-COMP-2026",
            "category": InventoryCategory.STUDY_KITS,
            "unit": "Kits",
            "stock": 45,
            "threshold": 10,
            "cost": 450.00,
            "location": "Warehouse B - Bay 1",
            "desc": "Complete kit including geometry box, notebooks, sketch pens, pouches, and ruler sets",
        },
        {
            "name": "Primary School Art & Craft Kit",
            "sku": "SK-ART-PRI",
            "category": InventoryCategory.STUDY_KITS,
            "unit": "Kits",
            "stock": 6,
            "threshold": 15,
            "cost": 220.00,
            "location": "Warehouse B - Bay 2",
            "desc": "Color pencils, crayons, modeling clay, and drawing pads",
        },

        # 4. Laptops (Bulk accessories / tracked items)
        {
            "name": "Dell Inspiron 3520 (Batch 2024)",
            "sku": "LP-DEL-3520",
            "category": InventoryCategory.LAPTOPS,
            "unit": "Units",
            "stock": 18,
            "threshold": 5,
            "cost": 38000.00,
            "location": "IT Asset Secure Locker 1",
            "desc": "Core i3 12th Gen, 8GB RAM, 512GB SSD for scholarship students",
        },
        {
            "name": "Lenovo V15 Laptop Power Adapters 65W",
            "sku": "LP-LEN-PWR",
            "category": InventoryCategory.LAPTOPS,
            "unit": "Pieces",
            "stock": 4,
            "threshold": 8,
            "cost": 1200.00,
            "location": "IT Asset Secure Locker 2",
            "desc": "Original replacement power supply adapters",
        },

        # 5. School Essentials
        {
            "name": "Ergonomic School Backpack - Medium",
            "sku": "SE-BAG-MED",
            "category": InventoryCategory.SCHOOL_ESSENTIALS,
            "unit": "Bags",
            "stock": 90,
            "threshold": 20,
            "cost": 350.00,
            "location": "Warehouse C - Aisle 1",
            "desc": "Durable water-resistant backpack with EduTrack branding",
        },
        {
            "name": "School Uniform Set (Girls - Medium)",
            "sku": "SE-UNI-GM",
            "category": InventoryCategory.SCHOOL_ESSENTIALS,
            "unit": "Sets",
            "stock": 50,
            "threshold": 15,
            "cost": 650.00,
            "location": "Warehouse C - Aisle 2",
            "desc": "Navy blue & white formal uniform set",
        },
        {
            "name": "Stainless Steel Water Bottles 750ml",
            "sku": "SE-BOT-750",
            "category": InventoryCategory.SCHOOL_ESSENTIALS,
            "unit": "Pieces",
            "stock": 5,
            "threshold": 25,
            "cost": 180.00,
            "location": "Warehouse C - Aisle 3",
            "desc": "Food grade insulated bottles for students",
        },

        # 6. Event Materials
        {
            "name": "Annual Science Fair Exhibition Banners",
            "sku": "EM-BAN-SCI",
            "category": InventoryCategory.EVENT_MATERIALS,
            "unit": "Rolls",
            "stock": 12,
            "threshold": 3,
            "cost": 800.00,
            "location": "Event Storage Room 101",
            "desc": "Vinyl backdrop banners and welcome signage",
        },
        {
            "name": "Sports Championship Medals & Trophies Set",
            "sku": "EM-MED-SET",
            "category": InventoryCategory.EVENT_MATERIALS,
            "unit": "Sets",
            "stock": 2,
            "threshold": 5,
            "cost": 2500.00,
            "location": "Event Storage Room 101",
            "desc": "Gold, Silver, Bronze medals and runner-up trophies",
        },
        {
            "name": "Portable PA System & Wireless Mic",
            "sku": "EM-AUD-PA1",
            "category": InventoryCategory.EVENT_MATERIALS,
            "unit": "Sets",
            "stock": 4,
            "threshold": 2,
            "cost": 15000.00,
            "location": "AV Media Locker",
            "desc": "Rechargeable portable sound system for school events",
        },
    ]

    for d in items_data:
        item = InventoryItem.objects.create(
            item_name=d["name"],
            sku=d["sku"],
            category=d["category"],
            unit=d["unit"],
            current_stock=d["stock"],
            low_stock_threshold=d["threshold"],
            unit_cost=Decimal(str(d["cost"])),
            location=d["location"],
            description=d["desc"],
        )
        if d["stock"] > 0:
            StockTransaction.objects.create(
                item=item,
                transaction_type=StockTransaction.TransactionType.STOCK_IN,
                quantity=d["stock"],
                previous_stock=0,
                new_stock=d["stock"],
                source_destination="Initial Procurement / CSR Inventory Donation",
                reference_number=f"INIT-{item.sku}",
                performed_by="System Admin",
                notes="Initial inventory setup",
            )

    # Seed Sample Laptops
    if not Laptop.objects.exists():
        laptops_sample = [
            ("AEQ-LP-001", "SN-DL940182", "Dell", "Inspiron 3520", 38000.00, Laptop.Condition.NEW, Laptop.Status.AVAILABLE),
            ("AEQ-LP-002", "SN-DL940183", "Dell", "Inspiron 3520", 38000.00, Laptop.Condition.NEW, Laptop.Status.AVAILABLE),
            ("AEQ-LP-003", "SN-LN773910", "Lenovo", "ThinkBook 15", 42000.00, Laptop.Condition.GOOD, Laptop.Status.AVAILABLE),
            ("AEQ-LP-004", "SN-HP551290", "HP", "ProBook 440", 45000.00, Laptop.Condition.GOOD, Laptop.Status.AVAILABLE),
            ("AEQ-LP-005", "SN-AC331899", "Acer", "TravelMate B3", 31000.00, Laptop.Condition.FAIR, Laptop.Status.DAMAGED),
        ]
        for asset, sn, brand, model, cost, cond, st in laptops_sample:
            Laptop.objects.create(
                asset_number=asset,
                serial_number=sn,
                brand=brand,
                model_name=model,
                purchase_cost=Decimal(str(cost)),
                condition=cond,
                status=st,
            )


@ensure_csrf_cookie
def inventory_portal(request):
    """
    Main Inventory Management Portal rendering single page dashboard with all 6 categories,
    stock in/out, low stock alerts, laptops, and transactions.
    """
    _ensure_initial_inventory_data()

    items = InventoryItem.objects.all()
    total_items = items.count()
    total_stock_units = items.aggregate(total=Sum("current_stock"))["total"] or 0
    low_stock_items = [i for i in items if i.is_low_stock]
    low_stock_count = len(low_stock_items)
    out_of_stock_count = items.filter(current_stock=0).count()

    laptops = Laptop.objects.all()
    laptops_total = laptops.count()
    laptops_available = laptops.filter(status=Laptop.Status.AVAILABLE).count()
    laptops_issued = laptops.filter(status=Laptop.Status.ISSUED).count()

    recent_transactions = StockTransaction.objects.select_related("item").order_by("-created_at")[:15]
    students = Student.objects.select_related("school").order_by("student_name")
    schools = School.objects.order_by("name")

    context = {
        "categories": InventoryCategory.choices,
        "items": items,
        "total_items": total_items,
        "total_stock_units": total_stock_units,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "laptops_total": laptops_total,
        "laptops_available": laptops_available,
        "laptops_issued": laptops_issued,
        "recent_transactions": recent_transactions,
        "students": students,
        "schools": schools,
        "user_authenticated": request.user.is_authenticated,
        "username": request.user.username if request.user.is_authenticated else "Admin",
    }
    return render(request, "inventory/portal.html", context)


# =============================================================================
# REST JSON APIS
# =============================================================================

def api_inventory_items(request):
    """List inventory items with search and filters"""
    query = request.GET.get("search", "").strip()
    category = request.GET.get("category", "").strip()
    status = request.GET.get("status", "").strip()

    items = InventoryItem.objects.all()

    if category:
        items = items.filter(category=category)

    if query:
        items = items.filter(
            Q(item_name__icontains=query) |
            Q(sku__icontains=query) |
            Q(location__icontains=query) |
            Q(description__icontains=query)
        )

    data = [_item_to_dict(i) for i in items]

    # Filter stock status if requested
    if status == "LOW_STOCK":
        data = [d for d in data if d["stock_status"] == "LOW_STOCK"]
    elif status == "OUT_OF_STOCK":
        data = [d for d in data if d["stock_status"] == "OUT_OF_STOCK"]
    elif status == "IN_STOCK":
        data = [d for d in data if d["stock_status"] == "IN_STOCK"]
    elif status == "ALERT":
        data = [d for d in data if d["is_low_stock"]]

    return JsonResponse({
        "success": True,
        "items": data,
        "count": len(data),
    })


@require_http_methods(["POST"])
def api_create_inventory_item(request):
    """Create a new inventory item"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        item_name = data.get("item_name", "").strip()
        sku = data.get("sku", "").strip()
        category = data.get("category", "").strip()
        unit = data.get("unit", "Pieces").strip()
        initial_stock = int(data.get("initial_stock") or 0)
        low_stock_threshold = int(data.get("low_stock_threshold") or 10)
        unit_cost = Decimal(str(data.get("unit_cost") or 0))
        location = data.get("location", "").strip()
        description = data.get("description", "").strip()

        if not item_name:
            return JsonResponse({"success": False, "error": "Item name is required."}, status=400)
        if not sku:
            return JsonResponse({"success": False, "error": "SKU / Item Code is required."}, status=400)
        if not category:
            return JsonResponse({"success": False, "error": "Category is required."}, status=400)

        if InventoryItem.objects.filter(sku__iexact=sku).exists():
            return JsonResponse({"success": False, "error": f"Item with SKU '{sku}' already exists."}, status=400)

        item = InventoryItem.objects.create(
            item_name=item_name,
            sku=sku,
            category=category,
            unit=unit,
            current_stock=initial_stock,
            low_stock_threshold=low_stock_threshold,
            unit_cost=unit_cost,
            location=location,
            description=description,
        )

        if initial_stock > 0:
            StockTransaction.objects.create(
                item=item,
                transaction_type=StockTransaction.TransactionType.STOCK_IN,
                quantity=initial_stock,
                previous_stock=0,
                new_stock=initial_stock,
                source_destination=data.get("source", "Initial Stock Entry"),
                reference_number=f"INIT-{sku}",
                performed_by=request.user.username if request.user.is_authenticated else "Admin",
                notes="Initial item creation stock",
            )

        return JsonResponse({
            "success": True,
            "message": f"Inventory item '{item.item_name}' created successfully!",
            "item": _item_to_dict(item),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_update_inventory_item(request, item_id):
    """Update details of an existing inventory item"""
    try:
        item = get_object_or_404(InventoryItem, id=item_id)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        if "item_name" in data and data["item_name"].strip():
            item.item_name = data["item_name"].strip()
        if "category" in data and data["category"].strip():
            item.category = data["category"].strip()
        if "unit" in data and data["unit"].strip():
            item.unit = data["unit"].strip()
        if "low_stock_threshold" in data and str(data["low_stock_threshold"]).isdigit():
            item.low_stock_threshold = int(data["low_stock_threshold"])
        if "unit_cost" in data:
            try:
                item.unit_cost = Decimal(str(data["unit_cost"]))
            except Exception:
                pass
        if "location" in data:
            item.location = data["location"].strip()
        if "description" in data:
            item.description = data["description"].strip()
        if "status" in data:
            item.status = data["status"]

        item.save()
        return JsonResponse({
            "success": True,
            "message": f"Item '{item.item_name}' updated successfully!",
            "item": _item_to_dict(item),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_delete_inventory_item(request, item_id):
    """Delete an inventory item"""
    try:
        item = get_object_or_404(InventoryItem, id=item_id)
        name = item.item_name
        item.delete()
        return JsonResponse({"success": True, "message": f"Item '{name}' deleted successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_stock_in(request):
    """Process Inward Stock (Stock In)"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        item_id = data.get("item_id")
        quantity = int(data.get("quantity") or 0)
        source = data.get("source", "").strip() or "Supplier / Vendor Intake"
        reference_no = data.get("reference_number", "").strip()
        notes = data.get("notes", "").strip()
        unit_cost = data.get("unit_cost")

        if not item_id:
            return JsonResponse({"success": False, "error": "Item ID is required."}, status=400)
        if quantity <= 0:
            return JsonResponse({"success": False, "error": "Quantity must be greater than zero."}, status=400)

        item = get_object_or_404(InventoryItem, id=item_id)
        cost_dec = Decimal(str(unit_cost)) if unit_cost else None

        performed_by = request.user.username if request.user.is_authenticated else "Admin"

        tx = process_stock_in(
            item=item,
            quantity=quantity,
            source_destination=source,
            reference_number=reference_no,
            performed_by=performed_by,
            notes=notes,
            unit_cost=cost_dec,
        )

        return JsonResponse({
            "success": True,
            "message": f"Stock In of {quantity} {item.unit} for '{item.item_name}' completed. Current Stock: {item.current_stock}.",
            "item": _item_to_dict(item),
            "transaction": _transaction_to_dict(tx),
        })
    except ValidationError as ve:
        return JsonResponse({"success": False, "error": str(ve.message if hasattr(ve, 'message') else ve)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_stock_out(request):
    """Process Outward Stock Dispatch (Stock Out)"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        item_id = data.get("item_id")
        quantity = int(data.get("quantity") or 0)
        destination = data.get("destination", "").strip() or "School / Student Distribution"
        reference_no = data.get("reference_number", "").strip()
        notes = data.get("notes", "").strip()

        if not item_id:
            return JsonResponse({"success": False, "error": "Item ID is required."}, status=400)
        if quantity <= 0:
            return JsonResponse({"success": False, "error": "Quantity must be greater than zero."}, status=400)

        item = get_object_or_404(InventoryItem, id=item_id)

        performed_by = request.user.username if request.user.is_authenticated else "Admin"

        tx = process_stock_out(
            item=item,
            quantity=quantity,
            source_destination=destination,
            reference_number=reference_no,
            performed_by=performed_by,
            notes=notes,
        )

        return JsonResponse({
            "success": True,
            "message": f"Stock Out of {quantity} {item.unit} for '{item.item_name}' processed. Remaining Stock: {item.current_stock}.",
            "item": _item_to_dict(item),
            "transaction": _transaction_to_dict(tx),
        })
    except ValidationError as ve:
        return JsonResponse({"success": False, "error": str(ve.message if hasattr(ve, 'message') else ve)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def api_stock_transactions(request):
    """Audit Trail / Ledger of all Stock Movements"""
    item_id = request.GET.get("item_id")
    tx_type = request.GET.get("type")
    category = request.GET.get("category")
    search = request.GET.get("search", "").strip()

    qs = StockTransaction.objects.select_related("item").all()

    if item_id:
        qs = qs.filter(item_id=item_id)
    if tx_type:
        qs = qs.filter(transaction_type=tx_type)
    if category:
        qs = qs.filter(item__category=category)
    if search:
        qs = qs.filter(
            Q(item__item_name__icontains=search) |
            Q(item__sku__icontains=search) |
            Q(source_destination__icontains=search) |
            Q(reference_number__icontains=search) |
            Q(notes__icontains=search)
        )

    data = [_transaction_to_dict(tx) for tx in qs[:100]]
    return JsonResponse({"success": True, "transactions": data, "count": len(data)})


def api_low_stock_alerts(request):
    """List all active Low Stock / Out of Stock alerts"""
    items = [i for i in InventoryItem.objects.all() if i.is_low_stock]
    data = [_item_to_dict(i) for i in items]
    return JsonResponse({
        "success": True,
        "alerts": data,
        "count": len(data),
    })


# =============================================================================
# LAPTOPS & IT ASSET MANAGEMENT
# =============================================================================

def api_laptops(request):
    """List all laptops with status and assignment details"""
    status = request.GET.get("status")
    search = request.GET.get("search", "").strip()

    qs = Laptop.objects.prefetch_related("assignments__student").all()

    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            Q(asset_number__icontains=search) |
            Q(serial_number__icontains=search) |
            Q(brand__icontains=search) |
            Q(model_name__icontains=search)
        )

    data = [_laptop_to_dict(l) for l in qs]
    return JsonResponse({"success": True, "laptops": data, "count": len(data)})


@require_http_methods(["POST"])
def api_create_laptop(request):
    """Register a new laptop in inventory"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        asset_number = data.get("asset_number", "").strip()
        serial_number = data.get("serial_number", "").strip()
        brand = data.get("brand", "").strip()
        model_name = data.get("model_name", "").strip()
        purchase_cost = data.get("purchase_cost")
        condition = data.get("condition", "NEW")
        notes = data.get("notes", "").strip()

        if not asset_number or not serial_number or not brand or not model_name:
            return JsonResponse({"success": False, "error": "Asset No, Serial No, Brand, and Model are required."}, status=400)

        if Laptop.objects.filter(asset_number__iexact=asset_number).exists():
            return JsonResponse({"success": False, "error": f"Asset number '{asset_number}' already exists."}, status=400)
        if Laptop.objects.filter(serial_number__iexact=serial_number).exists():
            return JsonResponse({"success": False, "error": f"Serial number '{serial_number}' already exists."}, status=400)

        cost_dec = Decimal(str(purchase_cost)) if purchase_cost else None

        laptop = Laptop.objects.create(
            asset_number=asset_number,
            serial_number=serial_number,
            brand=brand,
            model_name=model_name,
            purchase_cost=cost_dec,
            condition=condition,
            status=Laptop.Status.AVAILABLE,
            notes=notes,
        )

        return JsonResponse({
            "success": True,
            "message": f"Laptop {laptop.asset_number} registered successfully!",
            "laptop": _laptop_to_dict(laptop),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_issue_laptop(request):
    """Issue an available laptop to a student"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        laptop_id = data.get("laptop_id")
        student_id = data.get("student_id")
        academic_year = data.get("academic_year", "2026-27").strip()
        notes = data.get("notes", "").strip()

        if not laptop_id or not student_id:
            return JsonResponse({"success": False, "error": "Laptop and Student are required."}, status=400)

        laptop = get_object_or_404(Laptop, id=laptop_id)
        student = get_object_or_404(Student, id=student_id)

        assignment = issue_laptop(
            student=student,
            laptop=laptop,
            academic_year=academic_year,
            issue_notes=notes,
            bypass_eligibility=True,
        )

        return JsonResponse({
            "success": True,
            "message": f"Laptop {laptop.asset_number} successfully issued to {student.student_name}.",
            "assignment_id": assignment.id,
            "laptop": _laptop_to_dict(laptop),
        })
    except ValidationError as ve:
        return JsonResponse({"success": False, "error": str(ve.message if hasattr(ve, 'message') else ve)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_return_laptop(request, laptop_id):
    """Return an issued laptop"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        laptop = get_object_or_404(Laptop, id=laptop_id)
        assignment = laptop.assignments.filter(status=LaptopAssignment.Status.ISSUED).first()
        if not assignment:
            return JsonResponse({"success": False, "error": "No active assignment found for this laptop."}, status=400)

        return_notes = data.get("return_notes", "").strip()
        condition = data.get("condition", "GOOD")

        return_laptop(assignment, return_notes=return_notes, condition=condition)

        return JsonResponse({
            "success": True,
            "message": f"Laptop {laptop.asset_number} returned and marked Available.",
            "laptop": _laptop_to_dict(laptop),
        })
    except ValidationError as ve:
        return JsonResponse({"success": False, "error": str(ve.message if hasattr(ve, 'message') else ve)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# =============================================================================
# CSV EXPORTS
# =============================================================================

def api_export_csv(request):
    """Export inventory items or transaction history as CSV"""
    export_type = request.GET.get("type", "items")
    response = HttpResponse(content_type="text/csv")

    if export_type == "transactions":
        response["Content-Disposition"] = 'attachment; filename="inventory_transactions.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Time", "Item Name", "SKU", "Category", "Type", "Quantity", "Unit", "Prev Stock", "New Stock", "Source/Destination", "Reference #", "Performed By", "Notes"])
        for tx in StockTransaction.objects.select_related("item").all().order_by("-created_at"):
            writer.writerow([
                tx.transaction_date.strftime("%Y-%m-%d"),
                tx.created_at.strftime("%H:%M:%S"),
                tx.item.item_name,
                tx.item.sku,
                tx.item.get_category_display(),
                tx.get_transaction_type_display(),
                tx.quantity,
                tx.item.unit,
                tx.previous_stock,
                tx.new_stock,
                tx.source_destination,
                tx.reference_number,
                tx.performed_by,
                tx.notes,
            ])
    else:
        response["Content-Disposition"] = 'attachment; filename="inventory_stock_report.csv"'
        writer = csv.writer(response)
        writer.writerow(["Item Name", "SKU", "Category", "Current Stock", "Unit", "Low Stock Threshold", "Stock Status", "Unit Cost (INR)", "Location", "Description", "Last Updated"])
        for item in InventoryItem.objects.all().order_by("category", "item_name"):
            writer.writerow([
                item.item_name,
                item.sku,
                item.get_category_display(),
                item.current_stock,
                item.unit,
                item.low_stock_threshold,
                item.stock_status,
                f"{item.unit_cost:.2f}" if item.unit_cost else "0.00",
                item.location,
                item.description,
                item.updated_at.strftime("%Y-%m-%d %H:%M"),
            ])

    return response
