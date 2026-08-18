from django.shortcuts import render

from eligibility.models import EligibilityRecord, BenefitType


def internship_list(request):
    records = (
        EligibilityRecord.objects
        .filter(
            benefit_type=BenefitType.INTERNSHIP,
            eligible=True,
        )
        .select_related("student")
        .order_by("student__student_name")
    )

    return render(
        request,
        "internships/list.html",
        {
            "records": records,
        },
    )
