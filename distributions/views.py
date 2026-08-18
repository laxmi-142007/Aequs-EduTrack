import csv
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q

from .models import (
    Distribution,
    BenefitType,
    RecipientType,
    SchoolEssentialType,
    StudyKit,
    StudyKitItem,
)
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
from inventory.models import InventoryItem, Laptop, InventoryCategory


def _distribution_to_dict(dist):
    return {
        "id": dist.id,
        "benefit_type": dist.benefit_type,
        "benefit_type_display": dist.get_benefit_type_display(),
        "recipient_type": dist.recipient_type,
        "recipient_name": dist.student.student_name if dist.student else (dist.school.name if dist.school else "General"),
        "student_id": dist.student.id if dist.student else None,
        "student_name": dist.student.student_name if dist.student else None,
        "admission_number": dist.student.admission_number if dist.student else "",
        "student_class": dist.student.current_class if dist.student else "",
        "school_id": dist.school.id if dist.school else (dist.student.school.id if dist.student and dist.student.school else None),
        "school_name": dist.school.name if dist.school else (dist.student.school.name if dist.student and dist.student.school else "General"),
        "school_udise": dist.school.udise_code if dist.school else (dist.student.school.udise_code if dist.student and dist.student.school else ""),
        "item_id": dist.inventory_item.id if dist.inventory_item else None,
        "item_name": dist.inventory_item.item_name if dist.inventory_item else (dist.study_kit.name if dist.study_kit else "-"),
        "item_sku": dist.inventory_item.sku if dist.inventory_item else "",
        "item_unit": dist.inventory_item.unit if dist.inventory_item else "Units",
        "essential_type": dist.essential_item_type or "",
        "essential_type_display": dist.get_essential_item_type_display() if dist.essential_item_type else "",
        "study_kit_name": dist.study_kit.name if dist.study_kit else "",
        "quantity": dist.quantity,
        "academic_year": dist.academic_year,
        "distribution_date": dist.distribution_date.strftime("%Y-%m-%d"),
        "issued_by": dist.issued_by or "Admin",
        "remarks": dist.remarks or "",
        "created_at": dist.created_at.strftime("%Y-%m-%d %H:%M"),
    }
from django.shortcuts import render, redirect
from django.db.models import Sum
from .models import Distribution
from .forms import DistributionForm


def distribution_list(request):
    """View rendering the distribution list"""
    distributions = (
        Distribution.objects
        .select_related("student", "school", "inventory_item", "study_kit")
        .order_by("-distribution_date", "-created_at")
        .select_related("student")
        .order_by("-distribution_date", "-created_at")
    )

    total_distributions = distributions.count()

    students_benefited = (
        distributions.values("student").distinct().count()
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


def distribution_create(request):
    """View for creating a new distribution record via UI form"""
    from .forms import DistributionForm
    if request.method == "POST":
        form = DistributionForm(request.POST, skip_eligibility=True)
        if form.is_valid():
            dist = form.save(commit=False)
            if dist.student and dist.student.school and not dist.school:
                dist.school = dist.student.school
            if dist.student:
                dist.recipient_type = RecipientType.STUDENT
            elif dist.school:
                dist.recipient_type = RecipientType.SCHOOL

            if dist.inventory_item and dist.quantity > 0:
                from inventory.services import process_stock_out
                recipient_desc = f"{dist.student.student_name} ({dist.student.current_class})" if dist.student else f"School: {dist.school.name}"
                try:
                    process_stock_out(
                        item=dist.inventory_item,
                        quantity=dist.quantity,
                        source_destination=recipient_desc,
                        performed_by=dist.issued_by or "Admin",
                        notes=f"Distribution: {dist.remarks}",
                    )
                except Exception:
                    pass

            dist.save()
            return redirect("distributions:list")
    else:
        form = DistributionForm()

    return render(
        request,
        "distributions/distribution_form.html",
        {
            "form": form,
        },
    )


# =============================================================================
# REST APIS - ELIGIBILITY & ROSTERS
# =============================================================================

def api_eligible_students(request):
    """Fetch eligible students for a specific benefit (BOOK, WORKBOOK, STUDY_KIT, LAPTOP)"""
    benefit = request.GET.get("benefit_type", "BOOK").upper()
    students = get_eligible_students_for_benefit(benefit)

    data = [
        {
            "id": s.id,
            "name": s.student_name,
            "admission_number": s.admission_number,
            "current_class": s.current_class,
            "school_id": s.school.id if s.school else None,
            "school_name": s.school.name if s.school else "General",
        }
        for s in students
    ]
    return JsonResponse({"success": True, "students": data, "count": len(data)})


def api_top_puc_students(request):
    """Fetch Top 10 ranked PUC students for Laptop scholarship"""
    academic_year = request.GET.get("academic_year")
    top_students = get_top_puc_students(academic_year=academic_year, limit=10)
    return JsonResponse({"success": True, "top_students": top_students, "count": len(top_students)})


def api_study_kits(request):
    """List or create Study Kits"""
    if request.method == "POST":
        try:
            if request.content_type == "application/json":
                data = json.loads(request.body)
            else:
                data = request.POST

            name = data.get("name", "").strip()
            target_grade = data.get("target_grade_level", "Class 1 to 2nd PUC").strip()
            description = data.get("description", "").strip()
            items_list = data.get("items", [])

            if not name:
                return JsonResponse({"success": False, "error": "Kit Name is required."}, status=400)

            kit = StudyKit.objects.create(
                name=name,
                target_grade_level=target_grade,
                description=description,
            )

            for it in items_list:
                it_name = it.get("item_name", "").strip() if isinstance(it, dict) else str(it).strip()
                qty = int(it.get("quantity", 1)) if isinstance(it, dict) else 1
                if it_name:
                    StudyKitItem.objects.create(kit=kit, item_name=it_name, quantity_per_kit=qty)

            return JsonResponse({"success": True, "message": f"Study Kit '{kit.name}' created successfully!"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    kits = StudyKit.objects.prefetch_related("items").filter(is_active=True)
    data = [
        {
            "id": k.id,
            "name": k.name,
            "target_grade_level": k.target_grade_level,
            "description": k.description,
            "items": [
                {"item_name": it.item_name, "quantity": it.quantity_per_kit, "spec": it.specification}
                for it in k.items.all()
            ],
        }
        for k in kits
    ]
    return JsonResponse({"success": True, "kits": data, "count": len(data)})


# =============================================================================
# REST APIS - DISTRIBUTION TRANSACTIONS
# =============================================================================

@require_http_methods(["POST"])
def api_distribute_book(request):
    """Module 6: Distribute books to Class 1-10 students"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        student_id = data.get("student_id")
        item_id = data.get("item_id")
        quantity = int(data.get("quantity") or 1)
        academic_year = data.get("academic_year", "2026-27").strip()
        remarks = data.get("remarks", "").strip()

        if not student_id or not item_id:
            return JsonResponse({"success": False, "error": "Student and Book item are required."}, status=400)

        student = get_object_or_404(Student, id=student_id)
        item = get_object_or_404(InventoryItem, id=item_id)
        issued_by = request.user.username if request.user.is_authenticated else "Admin"

        dist = distribute_books(
            student=student,
            item=item,
            quantity=quantity,
            academic_year=academic_year,
            issued_by=issued_by,
            remarks=remarks,
        )

        return JsonResponse({
            "success": True,
            "message": f"Successfully distributed {quantity} copy of '{item.item_name}' to {student.student_name} ({student.current_class}). Inventory updated.",
            "distribution": _distribution_to_dict(dist),
        })
    except ValidationError as ve:
        return JsonResponse({"success": False, "error": str(ve.message if hasattr(ve, 'message') else ve)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_distribute_workbook(request):
    """Module 7: Distribute Workbooks to Class 10 students"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        student_id = data.get("student_id")
        item_id = data.get("item_id")
        quantity = int(data.get("quantity") or 1)
        academic_year = data.get("academic_year", "2026-27").strip()
        remarks = data.get("remarks", "").strip()

        if not student_id or not item_id:
            return JsonResponse({"success": False, "error": "Student and Workbook item are required."}, status=400)

        student = get_object_or_404(Student, id=student_id)
        item = get_object_or_404(InventoryItem, id=item_id)
        issued_by = request.user.username if request.user.is_authenticated else "Admin"

        dist = distribute_workbooks(
            student=student,
            item=item,
            quantity=quantity,
            academic_year=academic_year,
            issued_by=issued_by,
            remarks=remarks,
        )

        return JsonResponse({
            "success": True,
            "message": f"Successfully distributed {quantity} workbook '{item.item_name}' to {student.student_name} (Class 10). Inventory updated.",
            "distribution": _distribution_to_dict(dist),
        })
    except ValidationError as ve:
        return JsonResponse({"success": False, "error": str(ve.message if hasattr(ve, 'message') else ve)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_issue_study_kit(request):
    """Module 8: Issue Study Kit to students continuing up to 2nd PUC"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        student_id = data.get("student_id")
        item_id = data.get("item_id")
        kit_id = data.get("kit_id")
        quantity = int(data.get("quantity") or 1)
        academic_year = data.get("academic_year", "2026-27").strip()
        remarks = data.get("remarks", "").strip()

        if not student_id:
            return JsonResponse({"success": False, "error": "Student is required."}, status=400)

        student = get_object_or_404(Student, id=student_id)
        item = InventoryItem.objects.filter(id=item_id).first() if item_id else None
        kit = StudyKit.objects.filter(id=kit_id).first() if kit_id else None
        issued_by = request.user.username if request.user.is_authenticated else "Admin"

        dist = issue_study_kit(
            student=student,
            item=item,
            kit=kit,
            quantity=quantity,
            academic_year=academic_year,
            issued_by=issued_by,
            remarks=remarks,
        )

        return JsonResponse({
            "success": True,
            "message": f"Successfully issued Study Kit to {student.student_name} ({student.current_class}). Inventory updated.",
            "distribution": _distribution_to_dict(dist),
        })
    except ValidationError as ve:
        return JsonResponse({"success": False, "error": str(ve.message if hasattr(ve, 'message') else ve)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_issue_laptop_scholarship(request):
    """Module 9: Issue Laptop to Top PUC / Eligible Student"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        student_id = data.get("student_id")
        laptop_id = data.get("laptop_id")
        academic_year = data.get("academic_year", "2026-27").strip()
        notes = data.get("notes", "").strip()

        if not student_id or not laptop_id:
            return JsonResponse({"success": False, "error": "Student and Laptop asset are required."}, status=400)

        student = get_object_or_404(Student, id=student_id)
        laptop = get_object_or_404(Laptop, id=laptop_id)
        issued_by = request.user.username if request.user.is_authenticated else "Admin"

        assignment, dist = issue_laptop_scholarship(
            student=student,
            laptop=laptop,
            academic_year=academic_year,
            notes=notes,
            issued_by=issued_by,
        )

        return JsonResponse({
            "success": True,
            "message": f"Laptop {laptop.asset_number} ({laptop.brand} {laptop.model_name}) awarded to {student.student_name}.",
            "distribution": _distribution_to_dict(dist),
        })
    except ValidationError as ve:
        return JsonResponse({"success": False, "error": str(ve.message if hasattr(ve, 'message') else ve)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_distribute_school_essentials(request):
    """
    Module 12: Government School Essentials Distribution
    (Benches, Desks, Chairs, Whiteboards, Library Books, Lab Gear, Water Filters, Fans, Sports Kits, Projectors, etc.)
    """
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        school_id = data.get("school_id")
        item_id = data.get("item_id")
        essential_type = data.get("essential_type", "OTHER").strip()
        quantity = int(data.get("quantity") or 1)
        academic_year = data.get("academic_year", "2026-27").strip()
        remarks = data.get("remarks", "").strip()

        if not school_id or not item_id:
            return JsonResponse({"success": False, "error": "School and Essential inventory item are required."}, status=400)

        school = get_object_or_404(School, id=school_id)
        item = get_object_or_404(InventoryItem, id=item_id)
        issued_by = request.user.username if request.user.is_authenticated else "Admin"

        dist = distribute_school_essentials(
            school=school,
            item=item,
            essential_type=essential_type,
            quantity=quantity,
            academic_year=academic_year,
            issued_by=issued_by,
            remarks=remarks,
        )

        return JsonResponse({
            "success": True,
            "message": f"Successfully allocated {quantity} {item.unit} of '{item.item_name}' to {school.name}. School resources and inventory updated.",
            "distribution": _distribution_to_dict(dist),
        })
    except ValidationError as ve:
        return JsonResponse({"success": False, "error": str(ve.message if hasattr(ve, 'message') else ve)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# =============================================================================
# REST APIS - DISTRIBUTION HISTORY & REPORTS
# =============================================================================

def api_distribution_history(request):
    """Audit Trail / Log of all distributions"""
    benefit = request.GET.get("benefit_type")
    school_id = request.GET.get("school_id")
    student_id = request.GET.get("student_id")
    search = request.GET.get("search", "").strip()

    qs = Distribution.objects.select_related("student", "school", "inventory_item", "study_kit").all()

    if benefit:
        qs = qs.filter(benefit_type=benefit)
    if school_id:
        qs = qs.filter(Q(school_id=school_id) | Q(student__school_id=school_id))
    if student_id:
        qs = qs.filter(student_id=student_id)
    if search:
        qs = qs.filter(
            Q(student__student_name__icontains=search) |
            Q(student__admission_number__icontains=search) |
            Q(school__name__icontains=search) |
            Q(inventory_item__item_name__icontains=search) |
            Q(remarks__icontains=search)
        )

    data = [_distribution_to_dict(d) for d in qs[:100]]
    return JsonResponse({"success": True, "distributions": data, "count": len(data)})


def api_school_wise_report(request):
    """Aggregated School-wise distribution report"""
    schools = School.objects.all().order_by("name")
    report = []

    for sc in schools:
        dists = Distribution.objects.filter(Q(school=sc) | Q(student__school=sc))
        books_qty = dists.filter(benefit_type=BenefitType.BOOK).aggregate(total=Sum("quantity"))["total"] or 0
        workbooks_qty = dists.filter(benefit_type=BenefitType.WORKBOOK).aggregate(total=Sum("quantity"))["total"] or 0
        kits_qty = dists.filter(benefit_type=BenefitType.STUDY_KIT).aggregate(total=Sum("quantity"))["total"] or 0
        laptops_qty = dists.filter(benefit_type=BenefitType.LAPTOP).aggregate(total=Sum("quantity"))["total"] or 0
        essentials_qty = dists.filter(benefit_type=BenefitType.SCHOOL_ESSENTIAL).aggregate(total=Sum("quantity"))["total"] or 0

        report.append({
            "school_id": sc.id,
            "school_name": sc.name,
            "udise_code": sc.udise_code,
            "district": sc.district,
            "books_distributed": books_qty,
            "workbooks_distributed": workbooks_qty,
            "study_kits_distributed": kits_qty,
            "laptops_issued": laptops_qty,
            "school_essentials_units": essentials_qty,
            "total_items_delivered": books_qty + workbooks_qty + kits_qty + laptops_qty + essentials_qty,
        })

    return JsonResponse({"success": True, "report": report, "count": len(report)})


def api_student_wise_report(request):
    """Aggregated Student-wise distribution report"""
    query = request.GET.get("search", "").strip()
    students = Student.objects.select_related("school").all().order_by("student_name")

    if query:
        students = students.filter(
            Q(student_name__icontains=query) |
            Q(admission_number__icontains=query) |
            Q(school__name__icontains=query)
        )

    report = []
    for st in students:
        dists = Distribution.objects.filter(student=st)
        books_qty = dists.filter(benefit_type=BenefitType.BOOK).aggregate(total=Sum("quantity"))["total"] or 0
        workbooks_qty = dists.filter(benefit_type=BenefitType.WORKBOOK).aggregate(total=Sum("quantity"))["total"] or 0
        kits_qty = dists.filter(benefit_type=BenefitType.STUDY_KIT).aggregate(total=Sum("quantity"))["total"] or 0
        laptops_qty = dists.filter(benefit_type=BenefitType.LAPTOP).aggregate(total=Sum("quantity"))["total"] or 0

        report.append({
            "student_id": st.id,
            "student_name": st.student_name,
            "admission_number": st.admission_number,
            "current_class": st.current_class,
            "school_name": st.school.name if st.school else "General",
            "books_received": books_qty,
            "workbooks_received": workbooks_qty,
            "study_kits_received": kits_qty,
            "laptops_received": laptops_qty,
            "total_benefits": books_qty + workbooks_qty + kits_qty + laptops_qty,
        })

    return JsonResponse({"success": True, "report": report, "count": len(report)})


def api_export_distribution_csv(request):
    """Export distribution data as CSV"""
    report_type = request.GET.get("type", "school_wise")
    response = HttpResponse(content_type="text/csv")

    if report_type == "student_wise":
        response["Content-Disposition"] = 'attachment; filename="student_distribution_report.csv"'
        writer = csv.writer(response)
        writer.writerow(["Student Name", "Admission No", "Class", "School", "Books", "Workbooks", "Study Kits", "Laptops", "Total Items"])
        for st in Student.objects.select_related("school").all().order_by("student_name"):
            dists = Distribution.objects.filter(student=st)
            b = dists.filter(benefit_type=BenefitType.BOOK).aggregate(total=Sum("quantity"))["total"] or 0
            wb = dists.filter(benefit_type=BenefitType.WORKBOOK).aggregate(total=Sum("quantity"))["total"] or 0
            sk = dists.filter(benefit_type=BenefitType.STUDY_KIT).aggregate(total=Sum("quantity"))["total"] or 0
            lp = dists.filter(benefit_type=BenefitType.LAPTOP).aggregate(total=Sum("quantity"))["total"] or 0
            writer.writerow([
                st.student_name,
                st.admission_number,
                st.current_class,
                st.school.name if st.school else "General",
                b, wb, sk, lp, b + wb + sk + lp
            ])
    elif report_type == "history":
        response["Content-Disposition"] = 'attachment; filename="distribution_history.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Benefit Type", "Recipient Type", "Recipient / Student Name", "School", "Item Name", "Quantity", "Academic Year", "Issued By", "Remarks"])
        for d in Distribution.objects.select_related("student", "school", "inventory_item", "study_kit").all().order_by("-distribution_date"):
            writer.writerow([
                d.distribution_date.strftime("%Y-%m-%d"),
                d.get_benefit_type_display(),
                d.get_recipient_type_display(),
                d.student.student_name if d.student else (d.school.name if d.school else "General"),
                d.school.name if d.school else (d.student.school.name if d.student and d.student.school else ""),
                d.inventory_item.item_name if d.inventory_item else (d.study_kit.name if d.study_kit else "-"),
                d.quantity,
                d.academic_year,
                d.issued_by,
                d.remarks,
            ])
    else:
        response["Content-Disposition"] = 'attachment; filename="school_distribution_report.csv"'
        writer = csv.writer(response)
        writer.writerow(["School Name", "UDISE Code", "District", "Books Distributed", "Workbooks", "Study Kits", "Laptops", "School Essentials", "Total Delivered"])
        for sc in School.objects.all().order_by("name"):
            dists = Distribution.objects.filter(Q(school=sc) | Q(student__school=sc))
            b = dists.filter(benefit_type=BenefitType.BOOK).aggregate(total=Sum("quantity"))["total"] or 0
            wb = dists.filter(benefit_type=BenefitType.WORKBOOK).aggregate(total=Sum("quantity"))["total"] or 0
            sk = dists.filter(benefit_type=BenefitType.STUDY_KIT).aggregate(total=Sum("quantity"))["total"] or 0
            lp = dists.filter(benefit_type=BenefitType.LAPTOP).aggregate(total=Sum("quantity"))["total"] or 0
            se = dists.filter(benefit_type=BenefitType.SCHOOL_ESSENTIAL).aggregate(total=Sum("quantity"))["total"] or 0
            writer.writerow([
                sc.name,
                sc.udise_code,
                sc.district,
                b, wb, sk, lp, se, b + wb + sk + lp + se
            ])

    return response
