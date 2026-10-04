import csv
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from programs.models import MikePropenScholarshipApplication
from schools.models import School
from students.models import Student
from programs.metrics import normalize_academic_year


def propen_portal(request):
    """
    Mike Propen Scholarship Portal featuring:
    1. Analysis (Demographics, Acceptance Rate, Fund Allocation)
    2. Data Details (Searchable Application Roster & Workflow Status)
    3. Application Form (Online Registration & Review)
    """
    active_tab = request.GET.get("tab", "analysis").strip().lower()
    selected_ay = request.GET.get("ay", "2026-27").strip()
    status_filter = request.GET.get("status", "").strip()
    search_q = request.GET.get("q", "").strip()

    ay = normalize_academic_year(selected_ay)

    academic_years = [
        ("2026-27", "Current Year (2026-27)"),
        ("2025-26", "Academic Year 2025-26"),
        ("2024-25", "Academic Year 2024-25"),
        ("all", "All Years (Consolidated)"),
    ]

    base_qs = MikePropenScholarshipApplication.objects.all()
    if ay != "all":
        base_qs = base_qs.filter(academic_year=ay)

    # 1. ANALYSIS METRICS
    total_applicants = base_qs.count()
    awarded_count = base_qs.filter(
        status__in=[
            MikePropenScholarshipApplication.Status.AWARDED,
            MikePropenScholarshipApplication.Status.DISBURSED,
        ]
    ).count()
    disbursed_count = base_qs.filter(status=MikePropenScholarshipApplication.Status.DISBURSED).count()
    under_review_count = base_qs.filter(
        status__in=[
            MikePropenScholarshipApplication.Status.SUBMITTED,
            MikePropenScholarshipApplication.Status.UNDER_REVIEW,
            MikePropenScholarshipApplication.Status.INTERVIEW_SCHEDULED,
        ]
    ).count()

    total_sanctioned = base_qs.filter(
        status__in=[
            MikePropenScholarshipApplication.Status.AWARDED,
            MikePropenScholarshipApplication.Status.DISBURSED,
        ]
    ).aggregate(total=Sum("scholarship_amount"))["total"] or Decimal("0.00")

    total_disbursed = base_qs.filter(
        status=MikePropenScholarshipApplication.Status.DISBURSED
    ).aggregate(total=Sum("scholarship_amount"))["total"] or Decimal("0.00")

    avg_academic_pct = base_qs.aggregate(avg=Avg("academic_percentage"))["avg"] or 0.0

    acceptance_rate = 0.0
    if total_applicants > 0:
        acceptance_rate = round((awarded_count / total_applicants) * 100, 1)

    # Gender Breakdown
    female_count = base_qs.filter(gender__iexact="FEMALE").count()
    male_count = base_qs.filter(gender__iexact="MALE").count()
    other_gender_count = total_applicants - female_count - male_count
    female_pct = round((female_count / total_applicants * 100), 1) if total_applicants else 0.0
    male_pct = round((male_count / total_applicants * 100), 1) if total_applicants else 0.0

    # Grade Level Distribution
    grade_distribution = list(
        base_qs.values("grade_level").annotate(count=Count("id")).order_by("-count")
    )

    # Status Distribution
    status_distribution = list(
        base_qs.values("status").annotate(count=Count("id")).order_by("-count")
    )

    # 2. DATA DETAILS QUERY
    applications_qs = base_qs.select_related("student", "school")
    if status_filter:
        applications_qs = applications_qs.filter(status=status_filter)
    if search_q:
        applications_qs = applications_qs.filter(
            Q(student_name__icontains=search_q) |
            Q(application_number__icontains=search_q) |
            Q(school_name__icontains=search_q) |
            Q(contact_phone__icontains=search_q)
        )

    schools = School.objects.filter(status=School.Status.ACTIVE).order_by("name")

    context = {
        "active_tab": active_tab,
        "selected_ay": selected_ay,
        "academic_years": academic_years,
        "status_filter": status_filter,
        "search_q": search_q,
        "status_choices": MikePropenScholarshipApplication.Status.choices,
        "total_applicants": total_applicants,
        "awarded_count": awarded_count,
        "disbursed_count": disbursed_count,
        "under_review_count": under_review_count,
        "total_sanctioned": total_sanctioned,
        "total_disbursed": total_disbursed,
        "avg_academic_pct": round(avg_academic_pct, 1),
        "acceptance_rate": acceptance_rate,
        "female_count": female_count,
        "male_count": male_count,
        "other_gender_count": other_gender_count,
        "female_pct": female_pct,
        "male_pct": male_pct,
        "grade_distribution": grade_distribution,
        "status_distribution": status_distribution,
        "applications": applications_qs,
        "schools": schools,
    }
    return render(request, "programs/propen/portal.html", context)


def propen_apply(request):
    """Handles submission of a new Mike Propen Scholarship application."""
    if request.method == "POST":
        student_name = request.POST.get("student_name", "").strip()
        gender = request.POST.get("gender", "FEMALE").strip()
        school_id = request.POST.get("school")
        school_name = request.POST.get("school_name", "").strip()
        grade_level = request.POST.get("grade_level", "Class 10").strip()
        academic_percentage = request.POST.get("academic_percentage", "0").strip()
        annual_family_income = request.POST.get("annual_family_income", "0").strip()
        contact_phone = request.POST.get("contact_phone", "").strip()
        email = request.POST.get("email", "").strip()
        statement = request.POST.get("statement_of_purpose", "").strip()
        scholarship_amount = request.POST.get("scholarship_amount", "25000").strip()
        academic_year = request.POST.get("academic_year", "2026-27").strip()

        school_obj = None
        if school_id and school_id.isdigit():
            school_obj = School.objects.filter(pk=int(school_id)).first()
            if school_obj and not school_name:
                school_name = school_obj.name

        try:
            academic_pct_dec = Decimal(academic_percentage)
        except Exception:
            academic_pct_dec = Decimal("0.00")

        try:
            income_dec = Decimal(annual_family_income)
        except Exception:
            income_dec = Decimal("0.00")

        try:
            amount_dec = Decimal(scholarship_amount)
        except Exception:
            amount_dec = Decimal("25000.00")

        app = MikePropenScholarshipApplication.objects.create(
            student_name=student_name,
            gender=gender,
            school=school_obj,
            school_name=school_name or "Government Model High School",
            grade_level=grade_level,
            academic_percentage=academic_pct_dec,
            annual_family_income=income_dec,
            contact_phone=contact_phone,
            email=email,
            statement_of_purpose=statement,
            scholarship_amount=amount_dec,
            academic_year=academic_year,
            status=MikePropenScholarshipApplication.Status.SUBMITTED,
        )

        messages.success(
            request,
            f"Mike Propen Scholarship application '{app.application_number}' submitted successfully for {app.student_name}!"
        )
        return redirect(f"/scholarships/mike-propen/?tab=details")
    return redirect("/scholarships/mike-propen/?tab=apply")


def propen_update_status(request, pk):
    """Updates applicant workflow status and optional disbursement details."""
    app = get_object_or_404(MikePropenScholarshipApplication, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get("status")
        notes = request.POST.get("reviewer_notes", "").strip()

        if new_status in MikePropenScholarshipApplication.Status.values:
            app.status = new_status
            if notes:
                app.reviewer_notes = notes
            if new_status == MikePropenScholarshipApplication.Status.DISBURSED and not app.disbursement_date:
                app.disbursement_date = timezone.localdate()
            app.save()
            messages.success(request, f"Application {app.application_number} status updated to {app.get_status_display()}.")
    return redirect("/scholarships/mike-propen/?tab=details")


def propen_export_csv(request):
    """Exports all Mike Propen Scholarship applications to CSV format."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="mike_propen_scholarships.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Application Number",
        "Student Name",
        "Gender",
        "School",
        "Grade Level",
        "Academic %",
        "Annual Income (INR)",
        "Scholarship Amount (INR)",
        "Status",
        "Academic Year",
        "Application Date",
        "Disbursement Date",
        "Contact Phone",
        "Email",
    ])

    for app in MikePropenScholarshipApplication.objects.all().order_by("-application_date"):
        writer.writerow([
            app.application_number,
            app.student_name,
            app.gender,
            app.school_name,
            app.grade_level,
            app.academic_percentage,
            app.annual_family_income,
            app.scholarship_amount,
            app.get_status_display(),
            app.academic_year,
            app.application_date,
            app.disbursement_date or "",
            app.contact_phone,
            app.email,
        ])

    return response
