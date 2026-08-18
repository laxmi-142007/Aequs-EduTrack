from django.shortcuts import render
from .models import EligibilityRecord, BenefitType


def eligibility_list(request):

    records = EligibilityRecord.objects.select_related(
        "student"
    ).order_by("-checked_at")

    student = request.GET.get("student", "").strip()
    benefit = request.GET.get("benefit", "").strip()

    # Support both ?year=2026-27 and ?academic_year=2026-27
    academic_year = (
        request.GET.get("year")
        or request.GET.get("academic_year")
        or ""
    ).strip()

    eligible = request.GET.get("eligible", "").strip()
    rank = request.GET.get("rank", "").strip()

    # Student filter
    if student:
        records = records.filter(
            student__student_name__icontains=student
        )

    # Benefit filter
    if benefit:
        records = records.filter(
            benefit_type=benefit
        )

    # Academic year filter
    if academic_year:
        records = records.filter(
            academic_year=academic_year
        )

    # Eligibility filter
    if eligible == "yes":
        records = records.filter(
            eligible=True
        )
    elif eligible == "no":
        records = records.filter(
            eligible=False
        )

    # Rank filter
    if rank:
        try:
            records = records.filter(
                selection_rank=int(rank)
            )
        except ValueError:
            pass

    # Available academic years
    academic_years = (
        EligibilityRecord.objects
        .values_list("academic_year", flat=True)
        .distinct()
        .order_by("-academic_year")
    )

    return render(
        request,
        "eligibility/list.html",
        {
            "records": records,
            "benefit_types": BenefitType.choices,
            "academic_years": academic_years,

            "selected_student": student,
            "selected_benefit": benefit,
            "selected_academic_year": academic_year,
            "selected_eligible": eligible,
            "selected_rank": rank,
        },
    )
