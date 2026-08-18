import csv
import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count

from .models import EligibilityRecord, BenefitType
from .services import (
    generate_all_eligibility,
    create_or_update_eligibility,
    get_student_eligibility_profile,
    get_latest_academic_record,
    get_percentage,
)
from students.models import Student
from schools.models import School
from academics.models import AcademicRecord


def _record_to_dict(rec):
    student = rec.student
    school = student.school if student else None
    
    # Get academic record for this student and academic year if available
    acad_rec = get_latest_academic_record(student, rec.academic_year) if student else None
    pct = float(get_percentage(acad_rec)) if acad_rec else None

    return {
        "id": rec.id,
        "student_id": student.id if student else None,
        "student_name": student.student_name if student else "Unknown",
        "admission_number": student.admission_number if student else "N/A",
        "school_id": school.id if school else None,
        "school_name": school.name if school else "General",
        "school_district": school.district if school else "",
        "current_class": student.current_class if student else "",
        "gender": student.gender if student else "",
        "benefit_type": rec.benefit_type,
        "benefit_type_display": rec.get_benefit_type_display(),
        "academic_year": rec.academic_year,
        "eligible": rec.eligible,
        "selection_rank": rec.selection_rank,
        "percentage": pct,
        "reason": rec.reason or "",
        "checked_at": rec.checked_at.strftime("%Y-%m-%d %H:%M") if rec.checked_at else "",
    }


def _ensure_initial_eligibility_data():
    """Ensure sample eligibility records exist for initial preview if none present"""
    if EligibilityRecord.objects.exists():
        return
    
    # Auto-run for current academic years
    years = list(AcademicRecord.objects.values_list("academic_year", flat=True).distinct())
    if not years:
        years = ["2026-27", "2025-26", "2024-25"]
    
    for y in years:
        generate_all_eligibility(y)


@ensure_csrf_cookie
def eligibility_portal(request):
    """
    Main Eligibility Management Portal View rendering dashboard KPIs,
    benefit category tabs, evaluation engine, and live search/filter table.
    """
    _ensure_initial_eligibility_data()

    # Get distinct academic years from AcademicRecord and EligibilityRecord
    years_from_elig = list(EligibilityRecord.objects.values_list("academic_year", flat=True).distinct())
    years_from_acad = list(AcademicRecord.objects.values_list("academic_year", flat=True).distinct())
    all_years = sorted(list(set(years_from_elig + years_from_acad + ["2026-27", "2025-26", "2024-25"])), reverse=True)

    selected_year = request.GET.get("year", all_years[0] if all_years else "2026-27")

    # Base query for initial SSR
    qs = EligibilityRecord.objects.select_related("student", "student__school")
    if selected_year and selected_year != "ALL":
        qs = qs.filter(academic_year=selected_year)

    total_records = qs.count()
    total_eligible = qs.filter(eligible=True).count()
    total_ineligible = qs.filter(eligible=False).count()

    # Benefit breakdowns
    books_count = qs.filter(benefit_type=BenefitType.BOOK, eligible=True).count()
    workbooks_count = qs.filter(benefit_type=BenefitType.WORKBOOK, eligible=True).count()
    study_kits_count = qs.filter(benefit_type=BenefitType.STUDY_KIT, eligible=True).count()
    laptops_count = qs.filter(benefit_type=BenefitType.LAPTOP, eligible=True).count()
    internships_count = qs.filter(benefit_type=BenefitType.INTERNSHIP, eligible=True).count()

    schools = School.objects.order_by("name")
    students = Student.objects.select_related("school").filter(status=Student.Status.ACTIVE).order_by("student_name")

    benefit_choices = [
        {"code": BenefitType.BOOK, "label": "Books (Class 1-10)", "icon": "📚", "count": books_count},
        {"code": BenefitType.WORKBOOK, "label": "Workbook (Class 10)", "icon": "📝", "count": workbooks_count},
        {"code": BenefitType.STUDY_KIT, "label": "Study Kit (Merit & PUC)", "icon": "🎒", "count": study_kits_count},
        {"code": BenefitType.LAPTOP, "label": "Laptop (2nd PUC Merit)", "icon": "💻", "count": laptops_count},
        {"code": BenefitType.INTERNSHIP, "label": "Internship (Degree)", "icon": "💼", "count": internships_count},
    ]

    context = {
        "all_years": all_years,
        "selected_year": selected_year,
        "total_records": total_records,
        "total_eligible": total_eligible,
        "total_ineligible": total_ineligible,
        "books_count": books_count,
        "workbooks_count": workbooks_count,
        "study_kits_count": study_kits_count,
        "laptops_count": laptops_count,
        "internships_count": internships_count,
        "benefit_choices": benefit_choices,
        "schools": schools,
        "students": students,
        "records": qs.order_by("-eligible", "selection_rank", "student__student_name")[:100],
        "user_authenticated": request.user.is_authenticated,
        "username": request.user.username if request.user.is_authenticated else "Admin",
    }
    return render(request, "eligibility/portal.html", context)


# =========================================================================
# JSON REST APIS
# =========================================================================

def api_eligibility_records(request):
    """
    Search and filter eligibility records dynamically with JSON response.
    Supports query params: search, year, benefit_type, school, status, rank_only.
    """
    qs = EligibilityRecord.objects.select_related("student", "student__school").all()

    search = request.GET.get("search", "").strip()
    year = request.GET.get("year", "").strip()
    benefit = request.GET.get("benefit_type", "").strip()
    school_id = request.GET.get("school_id", "").strip()
    status = request.GET.get("status", "").strip()
    rank_only = request.GET.get("rank_only", "").strip()

    if year and year != "ALL":
        qs = qs.filter(academic_year=year)

    if benefit and benefit != "ALL":
        qs = qs.filter(benefit_type=benefit)

    if school_id and school_id != "ALL":
        qs = qs.filter(student__school_id=school_id)

    if status == "ELIGIBLE":
        qs = qs.filter(eligible=True)
    elif status == "INELIGIBLE":
        qs = qs.filter(eligible=False)

    if rank_only == "true":
        qs = qs.filter(selection_rank__isnull=False)

    if search:
        qs = qs.filter(
            Q(student__student_name__icontains=search) |
            Q(student__admission_number__icontains=search) |
            Q(student__school__name__icontains=search) |
            Q(reason__icontains=search) |
            Q(student__current_class__icontains=search)
        )

    # Order by merit rank first if available, then eligibility, then student name
    qs = qs.order_by("-eligible", "selection_rank", "student__student_name")

    data = [_record_to_dict(r) for r in qs]
    return JsonResponse({
        "success": True,
        "records": data,
        "count": len(data),
    })


def api_eligibility_summary(request):
    """
    Live KPI and category summary counts for a given academic year or overall.
    """
    year = request.GET.get("year", "").strip()
    qs = EligibilityRecord.objects.all()
    if year and year != "ALL":
        qs = qs.filter(academic_year=year)

    total_records = qs.count()
    total_eligible = qs.filter(eligible=True).count()
    total_ineligible = qs.filter(eligible=False).count()

    books_count = qs.filter(benefit_type=BenefitType.BOOK, eligible=True).count()
    workbooks_count = qs.filter(benefit_type=BenefitType.WORKBOOK, eligible=True).count()
    study_kits_count = qs.filter(benefit_type=BenefitType.STUDY_KIT, eligible=True).count()
    laptops_count = qs.filter(benefit_type=BenefitType.LAPTOP, eligible=True).count()
    internships_count = qs.filter(benefit_type=BenefitType.INTERNSHIP, eligible=True).count()

    return JsonResponse({
        "success": True,
        "summary": {
            "total_records": total_records,
            "total_eligible": total_eligible,
            "total_ineligible": total_ineligible,
            "books": books_count,
            "workbooks": workbooks_count,
            "study_kits": study_kits_count,
            "laptops": laptops_count,
            "internships": internships_count,
        }
    })


@require_http_methods(["POST"])
def api_run_evaluation(request):
    """
    Batch execution of eligibility evaluation engine for a specified academic year.
    """
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        academic_year = data.get("academic_year", "").strip()
        target_benefits = data.get("target_benefits", ["ALL"])

        if not academic_year:
            return JsonResponse({"success": False, "error": "Academic Year is required."}, status=400)

        # Execute batch engine
        result_metrics = generate_all_eligibility(academic_year, target_benefits=target_benefits)

        return JsonResponse({
            "success": True,
            "message": f"Eligibility Auto-Evaluation for {academic_year} completed successfully!",
            "metrics": result_metrics,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_create_eligibility_record(request):
    """
    Manually add or override a student's benefit eligibility record.
    """
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        student_id = data.get("student_id")
        benefit_type = data.get("benefit_type", "").strip()
        academic_year = data.get("academic_year", "").strip()
        eligible = data.get("eligible", True)
        selection_rank = data.get("selection_rank")
        reason = data.get("reason", "").strip()

        if isinstance(eligible, str):
            eligible = eligible.lower() in ["true", "1", "yes"]

        if not student_id:
            return JsonResponse({"success": False, "error": "Student is required."}, status=400)
        if not benefit_type:
            return JsonResponse({"success": False, "error": "Benefit Type is required."}, status=400)
        if not academic_year:
            return JsonResponse({"success": False, "error": "Academic Year is required."}, status=400)

        student = get_object_or_404(Student, id=student_id)

        rank_val = int(selection_rank) if selection_rank and str(selection_rank).isdigit() else None

        record = create_or_update_eligibility(
            student=student,
            benefit_type=benefit_type,
            academic_year=academic_year,
            eligible=eligible,
            selection_rank=rank_val,
            reason=reason or f"Manually configured eligibility record ({request.user.username if request.user.is_authenticated else 'Admin'}).",
        )

        return JsonResponse({
            "success": True,
            "message": f"Eligibility for {student.student_name} ({record.get_benefit_type_display()}) saved successfully.",
            "record": _record_to_dict(record),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_update_eligibility_record(request, record_id):
    """
    Update an existing eligibility record (status, rank, reason).
    """
    try:
        record = get_object_or_404(EligibilityRecord, id=record_id)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        if "eligible" in data:
            val = data["eligible"]
            if isinstance(val, str):
                record.eligible = val.lower() in ["true", "1", "yes"]
            else:
                record.eligible = bool(val)

        if "selection_rank" in data:
            sr = data["selection_rank"]
            record.selection_rank = int(sr) if sr and str(sr).isdigit() else None

        if "reason" in data:
            record.reason = data["reason"].strip()

        if "academic_year" in data and data["academic_year"].strip():
            record.academic_year = data["academic_year"].strip()

        record.save()

        return JsonResponse({
            "success": True,
            "message": "Eligibility record updated successfully.",
            "record": _record_to_dict(record),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_toggle_eligibility(request, record_id):
    """
    Quick one-click toggle for eligibility status.
    """
    try:
        record = get_object_or_404(EligibilityRecord, id=record_id)
        record.eligible = not record.eligible
        if not record.eligible and not record.reason.startswith("[Manual Override]"):
            record.reason = f"[Manual Override: Revoked] {record.reason}".strip()
        elif record.eligible and record.reason.startswith("[Manual Override: Revoked]"):
            record.reason = record.reason.replace("[Manual Override: Revoked]", "[Manual Override: Approved]").strip()
        record.save()

        return JsonResponse({
            "success": True,
            "message": f"Eligibility for {record.student.student_name} toggled to {'Eligible' if record.eligible else 'Not Eligible'}.",
            "eligible": record.eligible,
            "record": _record_to_dict(record),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_delete_eligibility_record(request, record_id):
    """
    Delete an eligibility record.
    """
    try:
        record = get_object_or_404(EligibilityRecord, id=record_id)
        st_name = record.student.student_name
        b_name = record.get_benefit_type_display()
        record.delete()
        return JsonResponse({
            "success": True,
            "message": f"Eligibility record for {st_name} ({b_name}) removed successfully.",
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def api_student_profile(request, student_id):
    """
    Returns 360-degree eligibility profile for a student across all 5 benefits.
    """
    student = get_object_or_404(Student, id=student_id)
    year = request.GET.get("year", None)
    profile = get_student_eligibility_profile(student, academic_year=year)
    return JsonResponse({"success": True, "profile": profile})


# =========================================================================
# CSV EXPORT
# =========================================================================

def export_eligibility_csv(request):
    """
    Generates downloadable CSV for government school / CSR distribution audit.
    """
    qs = EligibilityRecord.objects.select_related("student", "student__school").all()

    year = request.GET.get("year", "").strip()
    benefit = request.GET.get("benefit_type", "").strip()
    school_id = request.GET.get("school_id", "").strip()
    status = request.GET.get("status", "").strip()

    if year and year != "ALL":
        qs = qs.filter(academic_year=year)
    if benefit and benefit != "ALL":
        qs = qs.filter(benefit_type=benefit)
    if school_id and school_id != "ALL":
        qs = qs.filter(student__school_id=school_id)
    if status == "ELIGIBLE":
        qs = qs.filter(eligible=True)
    elif status == "INELIGIBLE":
        qs = qs.filter(eligible=False)

    qs = qs.order_by("-eligible", "selection_rank", "student__student_name")

    filename = f"Aequs_EduTrack_Eligibility_{year or 'All'}_{benefit or 'All'}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Record ID",
        "Student Name",
        "Admission Number",
        "Gender",
        "School Name",
        "School District",
        "Class / Standard",
        "Academic Year",
        "Benefit Type",
        "Eligible Status",
        "Selection Rank",
        "Evaluation Reason / Criteria",
        "Checked At",
    ])

    for rec in qs:
        st = rec.student
        sch = st.school if st else None
        writer.writerow([
            rec.id,
            st.student_name if st else "",
            st.admission_number if st else "",
            st.get_gender_display() if st else "",
            sch.name if sch else "",
            sch.district if sch else "",
            st.current_class if st else "",
            rec.academic_year,
            rec.get_benefit_type_display(),
            "Eligible" if rec.eligible else "Not Eligible",
            rec.selection_rank if rec.selection_rank else "-",
            rec.reason,
            rec.checked_at.strftime("%Y-%m-%d %H:%M") if rec.checked_at else "",
        ])

    return response
