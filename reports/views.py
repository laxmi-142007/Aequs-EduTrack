from django.shortcuts import render

from students.models import Student
from eligibility.models import EligibilityRecord, BenefitType


def report_list(request):

    academic_year = (
        request.GET.get("year")
        or request.GET.get("academic_year")
        or ""
    ).strip()

    eligibility_records = EligibilityRecord.objects.filter(
        eligible=True
    ).select_related("student")

    if academic_year:
        eligibility_records = eligibility_records.filter(
            academic_year=academic_year
        )

    total_students = Student.objects.filter(
        status=Student.Status.ACTIVE
    ).count()

    study_kit_count = eligibility_records.filter(
        benefit_type=BenefitType.STUDY_KIT
    ).count()

    laptop_count = eligibility_records.filter(
        benefit_type=BenefitType.LAPTOP
    ).count()

    book_count = eligibility_records.filter(
        benefit_type=BenefitType.BOOK
    ).count()

    workbook_count = eligibility_records.filter(
        benefit_type=BenefitType.WORKBOOK
    ).count()

    internship_count = eligibility_records.filter(
        benefit_type=BenefitType.INTERNSHIP
    ).count()

    academic_years = (
        EligibilityRecord.objects
        .values_list("academic_year", flat=True)
        .distinct()
        .order_by("-academic_year")
    )

    return render(
        request,
        "reports/list.html",
        {
            "total_students": total_students,
            "study_kit_count": study_kit_count,
            "laptop_count": laptop_count,
            "book_count": book_count,
            "workbook_count": workbook_count,
            "internship_count": internship_count,
            "academic_years": academic_years,
            "selected_academic_year": academic_year,
        },
    )
