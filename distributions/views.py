import json
import csv

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Count, Q

from .models import (
    Distribution,
    BenefitType,
    RecipientType,
    SchoolEssentialType,
    StudyKit,
    StudyKitItem,
)

from .forms import DistributionForm

from .services import (
    distribute_books,
    distribute_workbooks,
    issue_study_kit,
    issue_laptop_scholarship,
    distribute_school_essentials,
    get_top_puc_students,
    get_eligible_students_for_benefit,
)

from students.models import Student
from schools.models import School

from inventory.models import (
    InventoryItem,
    Laptop,
    InventoryCategory,
    StockTransaction,
)


# ============================================================
# HELPER
# ============================================================

def _distribution_to_dict(dist):
    return {
        "id": dist.id,
        "benefit_type": dist.benefit_type,
        "benefit_type_display": dist.get_benefit_type_display(),

        "recipient_type": dist.recipient_type,

        "recipient_name": (
            dist.student.student_name
            if dist.student
            else (
                dist.school.name
                if dist.school
                else "General"
            )
        ),

        "student_id": (
            dist.student.id
            if dist.student
            else None
        ),

        "student_name": (
            dist.student.student_name
            if dist.student
            else None
        ),

        "admission_number": (
            dist.student.admission_number
            if dist.student
            else ""
        ),

        "student_class": (
            dist.student.current_class
            if dist.student
            else ""
        ),

        "school_id": (
            dist.school.id
            if dist.school
            else (
                dist.student.school.id
                if dist.student and dist.student.school
                else None
            )
        ),

        "school_name": (
            dist.school.name
            if dist.school
            else (
                dist.student.school.name
                if dist.student and dist.student.school
                else "General"
            )
        ),

        "school_udise": (
            dist.school.udise_code
            if dist.school
            else (
                dist.student.school.udise_code
                if dist.student and dist.student.school
                else ""
            )
        ),

        "item_id": (
            dist.inventory_item.id
            if dist.inventory_item
            else None
        ),

        "item_name": (
            dist.inventory_item.item_name
            if dist.inventory_item
            else (
                dist.study_kit.name
                if dist.study_kit
                else "-"
            )
        ),

        "item_sku": (
            dist.inventory_item.sku
            if dist.inventory_item
            else ""
        ),

        "item_unit": (
            dist.inventory_item.unit
            if dist.inventory_item
            else "Units"
        ),

        "essential_type": dist.essential_item_type or "",

        "essential_type_display": (
            dist.get_essential_item_type_display()
            if dist.essential_item_type
            else ""
        ),

        "study_kit_name": (
            dist.study_kit.name
            if dist.study_kit
            else ""
        ),

        "quantity": dist.quantity,

        "academic_year": dist.academic_year,

        "distribution_date": (
            dist.distribution_date.strftime("%Y-%m-%d")
        ),

        "issued_by": dist.issued_by or "Admin",

        "remarks": dist.remarks or "",

        "created_at": (
            dist.created_at.strftime("%Y-%m-%d %H:%M")
        ),
    }


# ============================================================
# STOCK HELPERS
# ============================================================

def _stock_out(
    item,
    quantity,
    source_destination,
    performed_by,
    notes="",
):
    """
    Remove quantity from inventory and create STOCK_OUT transaction.
    """

    if not item or quantity <= 0:
        return

    item = InventoryItem.objects.select_for_update().get(
        pk=item.pk
    )

    if item.current_stock < quantity:
        raise ValidationError(
            f"Insufficient stock for '{item.item_name}'. "
            f"Available stock: {item.current_stock}. "
            f"Required: {quantity}."
        )

    previous_stock = item.current_stock

    item.current_stock -= quantity

    item.save(
        update_fields=[
            "current_stock",
            "updated_at",
        ]
    )

    StockTransaction.objects.create(
        item=item,
        transaction_type=StockTransaction.TransactionType.STOCK_OUT,
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=item.current_stock,
        source_destination=source_destination,
        performed_by=performed_by or "Admin",
        notes=notes,
    )


def _stock_in(
    item,
    quantity,
    source_destination,
    performed_by,
    notes="",
):
    """
    Return quantity to inventory and create STOCK_IN transaction.
    """

    if not item or quantity <= 0:
        return

    item = InventoryItem.objects.select_for_update().get(
        pk=item.pk
    )

    previous_stock = item.current_stock

    item.current_stock += quantity

    item.save(
        update_fields=[
            "current_stock",
            "updated_at",
        ]
    )

    StockTransaction.objects.create(
        item=item,
        transaction_type=StockTransaction.TransactionType.STOCK_IN,
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=item.current_stock,
        source_destination=source_destination,
        performed_by=performed_by or "Admin",
        notes=notes,
    )


# ============================================================
# DISTRIBUTION LIST
# ============================================================

def distribution_list(request):
    """
    Display all distribution records.
    """

    distributions = (
        Distribution.objects
        .select_related(
            "student",
            "student__school",
            "school",
            "inventory_item",
            "study_kit",
        )
        .order_by(
            "-distribution_date",
            "-created_at",
        )
    )

    total_distributions = distributions.count()

    students_benefited = (
        distributions
        .filter(student__isnull=False)
        .values("student")
        .distinct()
        .count()
    )

    total_quantity = (
        distributions.aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )

    return render(
        request,
        "distributions/distribution_list.html",
        {
            "distributions": distributions,
            "total_distributions": total_distributions,
            "students_benefited": students_benefited,
            "total_quantity": total_quantity,
        },
    )


# ============================================================
# CREATE DISTRIBUTION
# ============================================================

def distribution_create(request):
    """
    Create distribution.

    Inventory:
        Distribution 10
        Inventory 100
        Result 90
    """

    if request.method == "POST":

        form = DistributionForm(request.POST, skip_eligibility=True)

        if form.is_valid():

            try:

                with transaction.atomic():

                    dist = form.save(commit=False)

                    # Automatically assign student's school
                    if (
                        dist.student
                        and dist.student.school
                        and not dist.school
                    ):
                        dist.school = dist.student.school

                    # Recipient type
                    if dist.student:
                        dist.recipient_type = RecipientType.STUDENT

                    elif dist.school:
                        dist.recipient_type = RecipientType.SCHOOL

                    issued_by = (
                        dist.issued_by
                        or (
                            request.user.username
                            if request.user.is_authenticated
                            else "Admin"
                        )
                    )

                    # Inventory deduction
                    if (
                        dist.inventory_item
                        and dist.quantity
                        and dist.quantity > 0
                    ):

                        recipient_desc = (
                            f"{dist.student.student_name} "
                            f"({dist.student.current_class})"
                            if dist.student
                            else (
                                f"School: {dist.school.name}"
                                if dist.school
                                else "General"
                            )
                        )

                        _stock_out(
                            item=dist.inventory_item,
                            quantity=dist.quantity,
                            source_destination=recipient_desc,
                            performed_by=issued_by,
                            notes=(
                                f"Distribution created. "
                                f"{dist.remarks or ''}"
                            ),
                        )

                    dist.save()

                return redirect("distributions:list")

            except ValidationError as e:

                form.add_error(
                    "quantity",
                    str(e),
                )

        # Invalid form falls through

    else:
        form = DistributionForm()

    return render(
        request,
        "distributions/distribution_form.html",
        {
            "form": form,
        },
    )


# ============================================================
# EDIT DISTRIBUTION
# ============================================================

def distribution_edit(request, pk):
    """
    Edit an existing distribution.

    Same item:

        Old = 10
        New = 15
        Inventory -5

        Old = 15
        New = 8
        Inventory +7

    Different item:

        Old item + old quantity
        New item - new quantity
    """

    distribution = get_object_or_404(
        Distribution.objects.select_related(
            "student",
            "school",
            "inventory_item",
            "study_kit",
        ),
        pk=pk,
    )

    if request.method == "POST":

        old_quantity = distribution.quantity
        old_item_id = distribution.inventory_item_id

        form = DistributionForm(
            request.POST,
            instance=distribution,
        )

        if form.is_valid():

            try:

                with transaction.atomic():

                    # Save old item reference
                    old_item = None

                    if old_item_id:
                        old_item = (
                            InventoryItem.objects
                            .select_for_update()
                            .get(pk=old_item_id)
                        )

                    # Get new data
                    dist = form.save(commit=False)

                    # Automatically assign school
                    if (
                        dist.student
                        and dist.student.school
                        and not dist.school
                    ):
                        dist.school = dist.student.school

                    # Recipient type
                    if dist.student:
                        dist.recipient_type = RecipientType.STUDENT

                    elif dist.school:
                        dist.recipient_type = RecipientType.SCHOOL

                    issued_by = (
                        dist.issued_by
                        or (
                            request.user.username
                            if request.user.is_authenticated
                            else "Admin"
                        )
                    )

                    new_item = None

                    if dist.inventory_item_id:

                        new_item = (
                            InventoryItem.objects
                            .select_for_update()
                            .get(
                                pk=dist.inventory_item_id
                            )
                        )

                    # ==================================================
                    # SAME ITEM
                    # ==================================================

                    if old_item_id == dist.inventory_item_id:

                        if new_item:

                            difference = (
                                dist.quantity - old_quantity
                            )

                            # ------------------------------------------
                            # NEW QUANTITY IS GREATER
                            # ------------------------------------------

                            if difference > 0:

                                try:

                                    _stock_out(
                                        item=new_item,
                                        quantity=difference,
                                        source_destination=(
                                            f"Edit Distribution "
                                            f"#{distribution.id}"
                                        ),
                                        performed_by=issued_by,
                                        notes=(
                                            f"Quantity increased "
                                            f"from {old_quantity} "
                                            f"to {dist.quantity}."
                                        ),
                                    )

                                except ValidationError as e:

                                    form.add_error(
                                        "quantity",
                                        str(e),
                                    )

                                    return render(
                                        request,
                                        "distributions/distribution_form.html",
                                        {
                                            "form": form,
                                            "distribution": distribution,
                                            "is_edit": True,
                                        },
                                    )

                            # ------------------------------------------
                            # NEW QUANTITY IS SMALLER
                            # ------------------------------------------

                            elif difference < 0:

                                returned_quantity = abs(
                                    difference
                                )

                                _stock_in(
                                    item=new_item,
                                    quantity=returned_quantity,
                                    source_destination=(
                                        f"Edit Distribution "
                                        f"#{distribution.id}"
                                    ),
                                    performed_by=issued_by,
                                    notes=(
                                        f"Quantity decreased "
                                        f"from {old_quantity} "
                                        f"to {dist.quantity}. "
                                        f"Returned "
                                        f"{returned_quantity} "
                                        f"to inventory."
                                    ),
                                )

                    # ==================================================
                    # INVENTORY ITEM CHANGED
                    # ==================================================

                    else:

                        # ------------------------------------------
                        # RETURN OLD ITEM
                        # ------------------------------------------

                        if old_item:

                            _stock_in(
                                item=old_item,
                                quantity=old_quantity,
                                source_destination=(
                                    f"Edit Distribution "
                                    f"#{distribution.id}"
                                ),
                                performed_by=issued_by,
                                notes=(
                                    "Old inventory item returned "
                                    "because distribution item "
                                    "was changed."
                                ),
                            )

                        # ------------------------------------------
                        # REMOVE NEW ITEM
                        # ------------------------------------------

                        if new_item and dist.quantity > 0:

                            try:

                                _stock_out(
                                    item=new_item,
                                    quantity=dist.quantity,
                                    source_destination=(
                                        f"Edit Distribution "
                                        f"#{distribution.id}"
                                    ),
                                    performed_by=issued_by,
                                    notes=(
                                        "New inventory item "
                                        "deducted because "
                                        "distribution item "
                                        "was changed."
                                    ),
                                )

                            except ValidationError as e:

                                form.add_error(
                                    "quantity",
                                    str(e),
                                )

                                return render(
                                    request,
                                    "distributions/distribution_form.html",
                                    {
                                        "form": form,
                                        "distribution": distribution,
                                        "is_edit": True,
                                    },
                                )

                    # Save edited distribution
                    dist.save()

                return redirect("distributions:list")

            except ValidationError as e:

                form.add_error(
                    "quantity",
                    str(e),
                )

    else:

        form = DistributionForm(
            instance=distribution,
        )

    return render(
        request,
        "distributions/distribution_form.html",
        {
            "form": form,
            "distribution": distribution,
            "is_edit": True,
        },
    )


# ============================================================
# DELETE DISTRIBUTION
# ============================================================

@require_http_methods(["POST"])
def distribution_delete(request, pk):
    """
    Delete distribution.

    Example:

        Inventory = 90
        Distribution = 10

        Delete distribution

        Inventory = 100
    """

    with transaction.atomic():

        distribution = get_object_or_404(
            Distribution.objects.select_related(
                "inventory_item",
            ),
            pk=pk,
        )

        quantity = distribution.quantity

        item = None

        if distribution.inventory_item_id:

            item = (
                InventoryItem.objects
                .select_for_update()
                .get(
                    pk=distribution.inventory_item_id
                )
            )

        issued_by = (
            request.user.username
            if request.user.is_authenticated
            else "Admin"
        )

        # Return quantity to inventory
        if item and quantity > 0:

            _stock_in(
                item=item,
                quantity=quantity,
                source_destination=(
                    f"Deleted Distribution "
                    f"#{distribution.id}"
                ),
                performed_by=issued_by,
                notes=(
                    f"Distribution deleted. "
                    f"Returned {quantity} "
                    f"item(s) to inventory."
                ),
            )

        # Delete distribution only after stock is returned
        distribution.delete()

    return redirect("distributions:list")


# ============================================================
# API - ELIGIBLE STUDENTS
# ============================================================

def api_eligible_students(request):

    benefit = request.GET.get(
        "benefit_type",
        "BOOK",
    ).upper()

    academic_year = request.GET.get(
        "academic_year",
        "",
    ).strip()

    students = get_eligible_students_for_benefit(
        benefit,
        academic_year=academic_year or None,
    )

    data = [
        {
            "id": s.id,
            "name": s.student_name,
            "admission_number": s.admission_number,
            "current_class": s.current_class,
            "school_id": (
                s.school.id
                if s.school
                else None
            ),
            "school_name": (
                s.school.name
                if s.school
                else "General"
            ),
        }
        for s in students
    ]

    return JsonResponse(
        {
            "success": True,
            "students": data,
            "count": len(data),
        }
    )


# ============================================================
# API - TOP PUC STUDENTS
# ============================================================

def api_top_puc_students(request):

    academic_year = request.GET.get(
        "academic_year"
    )

    top_students = get_top_puc_students(
        academic_year=academic_year,
        limit=10,
    )

    return JsonResponse(
        {
            "success": True,
            "top_students": top_students,
            "count": len(top_students),
        }
    )


# ============================================================
# API - STUDY KITS
# ============================================================

def api_study_kits(request):

    if request.method == "POST":

        try:

            if request.content_type == "application/json":
                data = json.loads(request.body)

            else:
                data = request.POST

            name = data.get(
                "name",
                "",
            ).strip()

            target_grade = data.get(
                "target_grade_level",
                "Class 1 to 2nd PUC",
            ).strip()

            description = data.get(
                "description",
                "",
            ).strip()

            items_list = data.get(
                "items",
                [],
            )

            if not name:

                return JsonResponse(
                    {
                        "success": False,
                        "error": "Kit Name is required.",
                    },
                    status=400,
                )

            kit = StudyKit.objects.create(
                name=name,
                target_grade_level=target_grade,
                description=description,
            )

            for it in items_list:

                if isinstance(it, dict):

                    it_name = (
                        it.get(
                            "item_name",
                            "",
                        ).strip()
                    )

                    qty = int(
                        it.get(
                            "quantity",
                            1,
                        )
                    )

                else:

                    it_name = str(it).strip()
                    qty = 1

                if it_name:

                    StudyKitItem.objects.create(
                        kit=kit,
                        item_name=it_name,
                        quantity_per_kit=qty,
                    )

            return JsonResponse(
                {
                    "success": True,
                    "message": (
                        f"Study Kit '{kit.name}' "
                        f"created successfully!"
                    ),
                }
            )

        except Exception as e:

            return JsonResponse(
                {
                    "success": False,
                    "error": str(e),
                },
                status=500,
            )

    kits = (
        StudyKit.objects
        .prefetch_related("items")
        .filter(is_active=True)
    )

    data = [

        {
            "id": k.id,
            "name": k.name,
            "target_grade_level": (
                k.target_grade_level
            ),
            "description": k.description,

            "items": [

                {
                    "item_name": it.item_name,
                    "quantity": it.quantity_per_kit,
                    "spec": it.specification,
                }

                for it in k.items.all()
            ],
        }

        for k in kits
    ]

    return JsonResponse(
        {
            "success": True,
            "kits": data,
            "count": len(data),
        }
    )


# ============================================================
# API - DISTRIBUTE BOOK
# ============================================================

@require_http_methods(["POST"])
def api_distribute_book(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(request.body)

        else:
            data = request.POST

        student_id = data.get("student_id")
        item_id = data.get("item_id")

        quantity = int(
            data.get("quantity") or 1
        )

        academic_year = data.get(
            "academic_year",
            "2026-27",
        ).strip()

        remarks = data.get(
            "remarks",
            "",
        ).strip()

        if not student_id or not item_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Student and Book item "
                        "are required."
                    ),
                },
                status=400,
            )

        student = get_object_or_404(
            Student,
            id=student_id,
        )

        item = get_object_or_404(
            InventoryItem,
            id=item_id,
        )

        issued_by = (
            request.user.username
            if request.user.is_authenticated
            else "Admin"
        )

        dist = distribute_books(
            student=student,
            item=item,
            quantity=quantity,
            academic_year=academic_year,
            issued_by=issued_by,
            remarks=remarks,
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Successfully distributed "
                    f"{quantity} copy of "
                    f"'{item.item_name}' to "
                    f"{student.student_name}. "
                    f"Inventory updated."
                ),
                "distribution": (
                    _distribution_to_dict(dist)
                ),
            }
        )

    except ValidationError as ve:

        return JsonResponse(
            {
                "success": False,
                "error": str(ve),
            },
            status=400,
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# ============================================================
# API - DISTRIBUTE WORKBOOK
# ============================================================

@require_http_methods(["POST"])
def api_distribute_workbook(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(request.body)

        else:
            data = request.POST

        student_id = data.get("student_id")
        item_id = data.get("item_id")

        quantity = int(
            data.get("quantity") or 1
        )

        academic_year = data.get(
            "academic_year",
            "2026-27",
        ).strip()

        remarks = data.get(
            "remarks",
            "",
        ).strip()

        if not student_id or not item_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Student and Workbook "
                        "item are required."
                    ),
                },
                status=400,
            )

        student = get_object_or_404(
            Student,
            id=student_id,
        )

        item = get_object_or_404(
            InventoryItem,
            id=item_id,
        )

        issued_by = (
            request.user.username
            if request.user.is_authenticated
            else "Admin"
        )

        dist = distribute_workbooks(
            student=student,
            item=item,
            quantity=quantity,
            academic_year=academic_year,
            issued_by=issued_by,
            remarks=remarks,
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Successfully distributed "
                    f"{quantity} workbook "
                    f"'{item.item_name}' to "
                    f"{student.student_name}. "
                    f"Inventory updated."
                ),
                "distribution": (
                    _distribution_to_dict(dist)
                ),
            }
        )

    except ValidationError as ve:

        return JsonResponse(
            {
                "success": False,
                "error": str(ve),
            },
            status=400,
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# ============================================================
# API - STUDY KIT
# ============================================================

@require_http_methods(["POST"])
def api_issue_study_kit(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(request.body)

        else:
            data = request.POST

        student_id = data.get("student_id")
        item_id = data.get("item_id")
        kit_id = data.get("kit_id")

        quantity = int(
            data.get("quantity") or 1
        )

        academic_year = data.get(
            "academic_year",
            "2026-27",
        ).strip()

        remarks = data.get(
            "remarks",
            "",
        ).strip()

        if not student_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": "Student is required.",
                },
                status=400,
            )

        student = get_object_or_404(
            Student,
            id=student_id,
        )

        item = (
            InventoryItem.objects
            .filter(id=item_id)
            .first()
            if item_id
            else None
        )

        kit = (
            StudyKit.objects
            .filter(id=kit_id)
            .first()
            if kit_id
            else None
        )

        issued_by = (
            request.user.username
            if request.user.is_authenticated
            else "Admin"
        )

        dist = issue_study_kit(
            student=student,
            item=item,
            kit=kit,
            quantity=quantity,
            academic_year=academic_year,
            issued_by=issued_by,
            remarks=remarks,
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Successfully issued Study Kit "
                    f"to {student.student_name}. "
                    f"Inventory updated."
                ),
                "distribution": (
                    _distribution_to_dict(dist)
                ),
            }
        )

    except ValidationError as ve:

        return JsonResponse(
            {
                "success": False,
                "error": str(ve),
            },
            status=400,
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# ============================================================
# API - LAPTOP SCHOLARSHIP
# ============================================================

@require_http_methods(["POST"])
def api_issue_laptop_scholarship(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(request.body)

        else:
            data = request.POST

        student_id = data.get("student_id")
        laptop_id = data.get("laptop_id")

        academic_year = data.get(
            "academic_year",
            "2026-27",
        ).strip()

        notes = data.get(
            "notes",
            "",
        ).strip()

        if not student_id or not laptop_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Student and Laptop "
                        "asset are required."
                    ),
                },
                status=400,
            )

        student = get_object_or_404(
            Student,
            id=student_id,
        )

        laptop = get_object_or_404(
            Laptop,
            id=laptop_id,
        )

        issued_by = (
            request.user.username
            if request.user.is_authenticated
            else "Admin"
        )

        assignment, dist = issue_laptop_scholarship(
            student=student,
            laptop=laptop,
            academic_year=academic_year,
            notes=notes,
            issued_by=issued_by,
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Laptop {laptop.asset_number} "
                    f"awarded to "
                    f"{student.student_name}."
                ),
                "distribution": (
                    _distribution_to_dict(dist)
                ),
            }
        )

    except ValidationError as ve:

        return JsonResponse(
            {
                "success": False,
                "error": str(ve),
            },
            status=400,
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# ============================================================
# API - SCHOOL ESSENTIALS
# ============================================================

@require_http_methods(["POST"])
def api_distribute_school_essentials(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(request.body)

        else:
            data = request.POST

        school_id = data.get("school_id")
        item_id = data.get("item_id")

        essential_type = data.get(
            "essential_type",
            "OTHER",
        ).strip()

        quantity = int(
            data.get("quantity") or 1
        )

        academic_year = data.get(
            "academic_year",
            "2026-27",
        ).strip()

        remarks = data.get(
            "remarks",
            "",
        ).strip()

        if not school_id or not item_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "School and Essential "
                        "inventory item are required."
                    ),
                },
                status=400,
            )

        school = get_object_or_404(
            School,
            id=school_id,
        )

        item = get_object_or_404(
            InventoryItem,
            id=item_id,
        )

        issued_by = (
            request.user.username
            if request.user.is_authenticated
            else "Admin"
        )

        dist = distribute_school_essentials(
            school=school,
            item=item,
            essential_type=essential_type,
            quantity=quantity,
            academic_year=academic_year,
            issued_by=issued_by,
            remarks=remarks,
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Successfully allocated "
                    f"{quantity} {item.unit} of "
                    f"'{item.item_name}' to "
                    f"{school.name}. "
                    f"Inventory updated."
                ),
                "distribution": (
                    _distribution_to_dict(dist)
                ),
            }
        )

    except ValidationError as ve:

        return JsonResponse(
            {
                "success": False,
                "error": str(ve),
            },
            status=400,
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# ============================================================
# API - DISTRIBUTION HISTORY
# ============================================================

def api_distribution_history(request):

    benefit = request.GET.get(
        "benefit_type"
    )

    school_id = request.GET.get(
        "school_id"
    )

    student_id = request.GET.get(
        "student_id"
    )

    search = request.GET.get(
        "search",
        "",
    ).strip()

    qs = (
        Distribution.objects
        .select_related(
            "student",
            "school",
            "inventory_item",
            "study_kit",
        )
        .all()
    )

    if benefit:
        qs = qs.filter(
            benefit_type=benefit
        )

    if school_id:
        qs = qs.filter(
            Q(school_id=school_id)
            |
            Q(student__school_id=school_id)
        )

    if student_id:
        qs = qs.filter(
            student_id=student_id
        )

    if search:

        qs = qs.filter(
            Q(
                student__student_name__icontains=search
            )
            |
            Q(
                student__admission_number__icontains=search
            )
            |
            Q(
                school__name__icontains=search
            )
            |
            Q(
                inventory_item__item_name__icontains=search
            )
            |
            Q(
                remarks__icontains=search
            )
        )

    data = [
        _distribution_to_dict(d)
        for d in qs[:100]
    ]

    return JsonResponse(
        {
            "success": True,
            "distributions": data,
            "count": len(data),
        }
    )


# ============================================================
# API - SCHOOL REPORT
# ============================================================

def api_school_wise_report(request):

    schools = (
        School.objects
        .all()
        .order_by("name")
    )

    report = []

    for sc in schools:

        dists = Distribution.objects.filter(
            Q(school=sc)
            |
            Q(student__school=sc)
        )

        books_qty = (
            dists
            .filter(
                benefit_type=BenefitType.BOOK
            )
            .aggregate(total=Sum("quantity"))
            ["total"]
            or 0
        )

        workbooks_qty = (
            dists
            .filter(
                benefit_type=BenefitType.WORKBOOK
            )
            .aggregate(total=Sum("quantity"))
            ["total"]
            or 0
        )

        kits_qty = (
            dists
            .filter(
                benefit_type=BenefitType.STUDY_KIT
            )
            .aggregate(total=Sum("quantity"))
            ["total"]
            or 0
        )

        laptops_qty = (
            dists
            .filter(
                benefit_type=BenefitType.LAPTOP
            )
            .aggregate(total=Sum("quantity"))
            ["total"]
            or 0
        )

        essentials_qty = (
            dists
            .filter(
                benefit_type=BenefitType.SCHOOL_ESSENTIAL
            )
            .aggregate(total=Sum("quantity"))
            ["total"]
            or 0
        )

        report.append(
            {
                "school_id": sc.id,
                "school_name": sc.name,
                "udise_code": sc.udise_code,
                "district": sc.district,
                "books_distributed": books_qty,
                "workbooks_distributed": workbooks_qty,
                "study_kits_distributed": kits_qty,
                "laptops_issued": laptops_qty,
                "school_essentials_units": essentials_qty,
                "total_items_delivered": (
                    books_qty
                    + workbooks_qty
                    + kits_qty
                    + laptops_qty
                    + essentials_qty
                ),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "report": report,
            "count": len(report),
        }
    )


# ============================================================
# API - STUDENT REPORT
# ============================================================

def api_student_wise_report(request):

    query = request.GET.get(
        "search",
        "",
    ).strip()

    students = (
        Student.objects
        .select_related("school")
        .all()
        .order_by("student_name")
    )

    if query:

        students = students.filter(
            Q(
                student_name__icontains=query
            )
            |
            Q(
                admission_number__icontains=query
            )
            |
            Q(
                school__name__icontains=query
            )
        )

    report = []

    for st in students:

        dists = Distribution.objects.filter(
            student=st
        )

        books_qty = (
            dists
            .filter(
                benefit_type=BenefitType.BOOK
            )
            .aggregate(total=Sum("quantity"))
            ["total"]
            or 0
        )

        workbooks_qty = (
            dists
            .filter(
                benefit_type=BenefitType.WORKBOOK
            )
            .aggregate(total=Sum("quantity"))
            ["total"]
            or 0
        )

        kits_qty = (
            dists
            .filter(
                benefit_type=BenefitType.STUDY_KIT
            )
            .aggregate(total=Sum("quantity"))
            ["total"]
            or 0
        )

        laptops_qty = (
            dists
            .filter(
                benefit_type=BenefitType.LAPTOP
            )
            .aggregate(total=Sum("quantity"))
            ["total"]
            or 0
        )

        report.append(
            {
                "student_id": st.id,
                "student_name": st.student_name,
                "admission_number": st.admission_number,
                "current_class": st.current_class,
                "school_name": (
                    st.school.name
                    if st.school
                    else "General"
                ),
                "books_received": books_qty,
                "workbooks_received": workbooks_qty,
                "study_kits_received": kits_qty,
                "laptops_received": laptops_qty,
                "total_benefits": (
                    books_qty
                    + workbooks_qty
                    + kits_qty
                    + laptops_qty
                ),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "report": report,
            "count": len(report),
        }
    )


# ============================================================
# API - CSV EXPORT
# ============================================================

def api_export_distribution_csv(request):

    report_type = request.GET.get(
        "type",
        "school_wise",
    )

    response = HttpResponse(
        content_type="text/csv"
    )

    # --------------------------------------------------------
    # STUDENT WISE
    # --------------------------------------------------------

    if report_type == "student_wise":

        response[
            "Content-Disposition"
        ] = (
            'attachment; '
            'filename="student_distribution_report.csv"'
        )

        writer = csv.writer(response)

        writer.writerow(
            [
                "Student Name",
                "Admission No",
                "Class",
                "School",
                "Books",
                "Workbooks",
                "Study Kits",
                "Laptops",
                "Total Items",
            ]
        )

        for st in (
            Student.objects
            .select_related("school")
            .all()
            .order_by("student_name")
        ):

            dists = Distribution.objects.filter(
                student=st
            )

            b = (
                dists
                .filter(
                    benefit_type=BenefitType.BOOK
                )
                .aggregate(total=Sum("quantity"))
                ["total"]
                or 0
            )

            wb = (
                dists
                .filter(
                    benefit_type=BenefitType.WORKBOOK
                )
                .aggregate(total=Sum("quantity"))
                ["total"]
                or 0
            )

            sk = (
                dists
                .filter(
                    benefit_type=BenefitType.STUDY_KIT
                )
                .aggregate(total=Sum("quantity"))
                ["total"]
                or 0
            )

            lp = (
                dists
                .filter(
                    benefit_type=BenefitType.LAPTOP
                )
                .aggregate(total=Sum("quantity"))
                ["total"]
                or 0
            )

            writer.writerow(
                [
                    st.student_name,
                    st.admission_number,
                    st.current_class,
                    (
                        st.school.name
                        if st.school
                        else "General"
                    ),
                    b,
                    wb,
                    sk,
                    lp,
                    b + wb + sk + lp,
                ]
            )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    elif report_type == "history":

        response[
            "Content-Disposition"
        ] = (
            'attachment; '
            'filename="distribution_history.csv"'
        )

        writer = csv.writer(response)

        writer.writerow(
            [
                "Date",
                "Benefit Type",
                "Recipient Type",
                "Recipient / Student Name",
                "School",
                "Item Name",
                "Quantity",
                "Academic Year",
                "Issued By",
                "Remarks",
            ]
        )

        distributions = (
            Distribution.objects
            .select_related(
                "student",
                "school",
                "inventory_item",
                "study_kit",
            )
            .all()
            .order_by(
                "-distribution_date"
            )
        )

        for d in distributions:

            writer.writerow(
                [
                    d.distribution_date.strftime(
                        "%Y-%m-%d"
                    ),

                    d.get_benefit_type_display(),

                    d.get_recipient_type_display(),

                    (
                        d.student.student_name
                        if d.student
                        else (
                            d.school.name
                            if d.school
                            else "General"
                        )
                    ),

                    (
                        d.school.name
                        if d.school
                        else (
                            d.student.school.name
                            if (
                                d.student
                                and d.student.school
                            )
                            else ""
                        )
                    ),

                    (
                        d.inventory_item.item_name
                        if d.inventory_item
                        else (
                            d.study_kit.name
                            if d.study_kit
                            else "-"
                        )
                    ),

                    d.quantity,

                    d.academic_year,

                    d.issued_by,

                    d.remarks,
                ]
            )

    # --------------------------------------------------------
    # SCHOOL WISE
    # --------------------------------------------------------

    else:

        response[
            "Content-Disposition"
        ] = (
            'attachment; '
            'filename="school_distribution_report.csv"'
        )

        writer = csv.writer(response)

        writer.writerow(
            [
                "School Name",
                "UDISE Code",
                "District",
                "Books Distributed",
                "Workbooks",
                "Study Kits",
                "Laptops",
                "School Essentials",
                "Total Delivered",
            ]
        )

        for sc in (
            School.objects
            .all()
            .order_by("name")
        ):

            dists = Distribution.objects.filter(
                Q(school=sc)
                |
                Q(student__school=sc)
            )

            b = (
                dists
                .filter(
                    benefit_type=BenefitType.BOOK
                )
                .aggregate(total=Sum("quantity"))
                ["total"]
                or 0
            )

            wb = (
                dists
                .filter(
                    benefit_type=BenefitType.WORKBOOK
                )
                .aggregate(total=Sum("quantity"))
                ["total"]
                or 0
            )

            sk = (
                dists
                .filter(
                    benefit_type=BenefitType.STUDY_KIT
                )
                .aggregate(total=Sum("quantity"))
                ["total"]
                or 0
            )

            lp = (
                dists
                .filter(
                    benefit_type=BenefitType.LAPTOP
                )
                .aggregate(total=Sum("quantity"))
                ["total"]
                or 0
            )

            se = (
                dists
                .filter(
                    benefit_type=BenefitType.SCHOOL_ESSENTIAL
                )
                .aggregate(total=Sum("quantity"))
                ["total"]
                or 0
            )

            writer.writerow(
                [
                    sc.name,
                    sc.udise_code,
                    sc.district,
                    b,
                    wb,
                    sk,
                    lp,
                    se,
                    b + wb + sk + lp + se,
                ]
            )

    return response



