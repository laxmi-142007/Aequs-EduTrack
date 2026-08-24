from django.shortcuts import render
from students.models import Student
from eligibility.models import EligibilityRecord, BenefitType
from reports.models import ActivityLog, log_activity


def report_list(request):
    academic_year = (
        request.GET.get("year")
        or request.GET.get("academic_year")
        or ""
    ).strip()

    category_filter = request.GET.get("category", "").strip().upper()

    # Seed demo logs if database is empty
    if not ActivityLog.objects.exists():
        user = request.user if request.user.is_authenticated else None
        log_activity(user, "Dispatched 50 Textbook Sets to Govt Model School Jayanagar", "INVENTORY")
        log_activity(user, "Registered new school Govt High School Belagavi", "SCHOOL")
        log_activity(user, "Updated Headmaster profile for Govt Composite PU College", "SCHOOL")
        log_activity(user, "Enrolled 12 new students in Class 8", "STUDENT")
        log_activity(user, "System Administrator Logged In", "AUTH")

    activity_logs = ActivityLog.objects.select_related("user").all()

    if category_filter:
        activity_logs = activity_logs.filter(category=category_filter)

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
            "activity_logs": activity_logs[:50],
            "category_filter": category_filter,
        },
    )


def api_activity_logs(request):
    category_filter = request.GET.get("category", "").strip().upper()
    logs = ActivityLog.objects.select_related("user").all()
    if category_filter:
        logs = logs.filter(category=category_filter)
    
    data = []
    for l in logs[:50]:
        data.append({
            "id": l.id,
            "timestamp": l.timestamp.strftime("%b %d, %Y %H:%M:%S"),
            "category": l.category,
            "action": l.action,
            "username": l.user.username if l.user else "System Admin",
            "details": l.details or "",
        })
    return JsonResponse({"success": True, "logs": data})
