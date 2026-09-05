from datetime import datetime, time, timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from students.models import Student
from eligibility.models import EligibilityRecord, BenefitType
from .models import ActivityLog


# =============================================================================
# REPORT LIST
# =============================================================================

def report_list(request):
    """
    Main Reports page.

    Shows:
    - Student statistics
    - Inventory/benefit statistics
    - Activity audit logs
    - Category filtering
    - Date range filtering
    - Action type filtering
    """

    # -------------------------------------------------------------------------
    # FILTERS
    # -------------------------------------------------------------------------

    academic_year = (
        request.GET.get("year")
        or request.GET.get("academic_year")
        or ""
    ).strip()

    category_filter = (
        request.GET.get("category", "")
        .strip()
        .upper()
    )

    action_type_filter = (
        request.GET.get("action_type", "")
        .strip()
        .upper()
    )

    date_from = (
        request.GET.get("date_from", "")
        .strip()
    )

    date_to = (
        request.GET.get("date_to", "")
        .strip()
    )

    # -------------------------------------------------------------------------
    # ACTIVITY LOGS
    # -------------------------------------------------------------------------

    activity_logs = (
        ActivityLog.objects
        .select_related("user")
        .all()
    )

    # Category filter
    if category_filter:
        activity_logs = activity_logs.filter(
            category=category_filter
        )

    # Action type filter
    if action_type_filter:
        activity_logs = activity_logs.filter(
            action_type=action_type_filter
        )

    # -------------------------------------------------------------------------
    # DATE FILTER
    #
    # date_from:
    #     Includes the entire selected starting day.
    #
    # date_to:
    #     Includes the entire selected ending day.
    # -------------------------------------------------------------------------

    parsed_date_from = None
    parsed_date_to = None

    try:
        if date_from:
            parsed_date_from = datetime.strptime(
                date_from,
                "%Y-%m-%d"
            ).date()

            start_datetime = timezone.make_aware(
                datetime.combine(
                    parsed_date_from,
                    time.min
                )
            )

            activity_logs = activity_logs.filter(
                timestamp__gte=start_datetime
            )

    except ValueError:
        date_from = ""

    try:
        if date_to:
            parsed_date_to = datetime.strptime(
                date_to,
                "%Y-%m-%d"
            ).date()

            # Use the next day at midnight.
            # This includes the complete selected date.
            end_datetime = timezone.make_aware(
                datetime.combine(
                    parsed_date_to + timedelta(days=1),
                    time.min
                )
            )

            activity_logs = activity_logs.filter(
                timestamp__lt=end_datetime
            )

    except ValueError:
        date_to = ""

    # -------------------------------------------------------------------------
    # ELIGIBILITY / BENEFIT DATA
    # -------------------------------------------------------------------------

    eligibility_records = (
        EligibilityRecord.objects
        .filter(eligible=True)
        .select_related("student")
    )

    if academic_year:
        eligibility_records = eligibility_records.filter(
            academic_year=academic_year
        )

    # -------------------------------------------------------------------------
    # STUDENT COUNT
    # -------------------------------------------------------------------------

    total_students = (
        Student.objects
        .filter(status=Student.Status.ACTIVE)
        .count()
    )

    # -------------------------------------------------------------------------
    # BENEFIT COUNTS
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # ACADEMIC YEARS
    # -------------------------------------------------------------------------

    academic_years = (
        EligibilityRecord.objects
        .values_list(
            "academic_year",
            flat=True,
        )
        .distinct()
        .order_by("-academic_year")
    )

    # -------------------------------------------------------------------------
    # CATEGORY LIST
    # -------------------------------------------------------------------------

    categories = [
        {
            "value": "STUDENT",
            "label": "Students",
        },
        {
            "value": "ACADEMIC",
            "label": "Academics",
        },
        {
            "value": "INVENTORY",
            "label": "Inventory",
        },
        {
            "value": "SCHOOL",
            "label": "Schools",
        },
        {
            "value": "EVENT",
            "label": "Events",
        },
        {
            "value": "DISTRIBUTION",
            "label": "Distributions",
        },
        {
            "value": "INTERNSHIP",
            "label": "Internships",
        },
        {
            "value": "VOLUNTEER",
            "label": "Volunteers",
        },
    ]

    # -------------------------------------------------------------------------
    # ACTION TYPE LIST
    # -------------------------------------------------------------------------

    action_types = [
        {
            "value": "CREATE",
            "label": "Created",
        },
        {
            "value": "UPDATE",
            "label": "Updated",
        },
        {
            "value": "DELETE",
            "label": "Deleted",
        },
        {
            "value": "LOGIN",
            "label": "Logged In",
        },
        {
            "value": "LOGOUT",
            "label": "Logged Out",
        },
        {
            "value": "VIEW",
            "label": "Viewed",
        },
        {
            "value": "EXPORT",
            "label": "Exported",
        },
        {
            "value": "IMPORT",
            "label": "Imported",
        },
        {
            "value": "OTHER",
            "label": "Other",
        },
    ]

    # -------------------------------------------------------------------------
    # CONTEXT
    # -------------------------------------------------------------------------

    context = {
        "total_students": total_students,

        "study_kit_count": study_kit_count,
        "laptop_count": laptop_count,
        "book_count": book_count,
        "workbook_count": workbook_count,
        "internship_count": internship_count,

        "academic_years": academic_years,
        "selected_academic_year": academic_year,

        "activity_logs": activity_logs[:100],

        "category_filter": category_filter,
        "action_type_filter": action_type_filter,

        "date_from": date_from,
        "date_to": date_to,

        "categories": categories,
        "action_types": action_types,
    }

    return render(
        request,
        "reports/list.html",
        context,
    )


# =============================================================================
# ACTIVITY LOG API
# =============================================================================

def api_activity_logs(request):
    """
    Returns the latest activity logs as JSON.

    Supported filters:

        /reports/api/logs/

        /reports/api/logs/?category=INVENTORY

        /reports/api/logs/?category=STUDENT

        /reports/api/logs/?date_from=2026-09-01

        /reports/api/logs/?date_to=2026-09-05

        /reports/api/logs/?date_from=2026-09-01&date_to=2026-09-05

        /reports/api/logs/?category=INVENTORY&date_from=2026-09-01&date_to=2026-09-05
    """

    # -------------------------------------------------------------------------
    # FILTERS
    # -------------------------------------------------------------------------

    category_filter = (
        request.GET.get("category", "")
        .strip()
        .upper()
    )

    action_type_filter = (
        request.GET.get("action_type", "")
        .strip()
        .upper()
    )

    date_from = (
        request.GET.get("date_from", "")
        .strip()
    )

    date_to = (
        request.GET.get("date_to", "")
        .strip()
    )

    # -------------------------------------------------------------------------
    # QUERY
    # -------------------------------------------------------------------------

    logs = (
        ActivityLog.objects
        .select_related("user")
        .all()
    )

    # Category
    if category_filter:
        logs = logs.filter(
            category=category_filter
        )

    # Action type
    if action_type_filter:
        logs = logs.filter(
            action_type=action_type_filter
        )

    # -------------------------------------------------------------------------
    # DATE FROM
    # -------------------------------------------------------------------------

    try:

        if date_from:

            parsed_date_from = datetime.strptime(
                date_from,
                "%Y-%m-%d"
            ).date()

            start_datetime = timezone.make_aware(
                datetime.combine(
                    parsed_date_from,
                    time.min
                )
            )

            logs = logs.filter(
                timestamp__gte=start_datetime
            )

    except ValueError:

        date_from = ""

    # -------------------------------------------------------------------------
    # DATE TO
    # -------------------------------------------------------------------------

    try:

        if date_to:

            parsed_date_to = datetime.strptime(
                date_to,
                "%Y-%m-%d"
            ).date()

            end_datetime = timezone.make_aware(
                datetime.combine(
                    parsed_date_to + timedelta(days=1),
                    time.min
                )
            )

            logs = logs.filter(
                timestamp__lt=end_datetime
            )

    except ValueError:

        date_to = ""

    # -------------------------------------------------------------------------
    # SERIALIZE
    # -------------------------------------------------------------------------

    data = []

    for log in logs[:100]:

        username = (
            log.user.username
            if log.user
            else "System"
        )

        data.append({
            "id": log.id,

            "timestamp": (
                log.timestamp.strftime(
                    "%b %d, %Y %H:%M:%S"
                )
            ),

            "category": (
                log.category or "GENERAL"
            ),

            "action_type": (
                log.action_type or "OTHER"
            ),

            "action": (
                log.action or ""
            ),

            "username": username,

            "performed_by": username,

            "object_type": (
                log.object_type or ""
            ),

            "object_id": (
                log.object_id or ""
            ),

            "details": (
                log.details or ""
            ),
        })

    return JsonResponse({
        "success": True,
        "logs": data,
        "count": len(data),
    })
