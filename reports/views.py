import csv
from datetime import datetime, time, timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from eligibility.models import BenefitType, EligibilityRecord
from reports.forms import ReportForm
from reports.models import ActivityLog, Report, log_activity
from students.models import Student

User = get_user_model()


def can_edit_reports(user):
    """
    Checks whether a user has permission to create, edit, or delete reports.
    Permitted if user is admin, superuser, staff, or has add/change_report permission.
    """
    if not user or not user.is_authenticated:
        return False
    return (
        getattr(user, "is_admin", False)
        or getattr(user, "is_superuser", False)
        or getattr(user, "is_staff", False)
        or user.has_perm("reports.add_report")
        or user.has_perm("reports.change_report")
    )


# =============================================================================
# REPORT LIST
# =============================================================================

def report_list(request):
    """
    Main Reports page.

    Shows:
    - Student statistics
    - Inventory/benefit statistics
    - Saved / Configured Reports Hub
    - Real-time Activity audit logs with Category, Date range, and Action type filtering
    """

    # -------------------------------------------------------------------------
    # FILTERS
    # -------------------------------------------------------------------------

    academic_year = (
        request.GET.get("year")
        or request.GET.get("academic_year")
        or ""
    ).strip()

    category_filter = request.GET.get("category", "").strip().upper()
    action_type_filter = request.GET.get("action_type", "").strip().upper()
    type_filter = request.GET.get("type", "").strip()
    scope_filter = request.GET.get("scope", "").strip()
    status_filter = request.GET.get("status", "").strip()

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    # -------------------------------------------------------------------------
    # SEED DEFAULT REPORTS
    # -------------------------------------------------------------------------

    if not Report.objects.exists():
        admin_user = User.objects.filter(is_superuser=True).first() or (
            request.user if request.user.is_authenticated else None
        )
        Report.objects.create(
            title="Comprehensive Student Enrollment & Demographics",
            report_type=Report.ReportType.STUDENT_DEMOGRAPHICS,
            description="Overview of all student enrollments across partner schools with gender breakdown.",
            visibility=Report.Visibility.PUBLIC,
            created_by=admin_user,
        )
        Report.objects.create(
            title="Benefit & Study Kit Eligibility Summary",
            report_type=Report.ReportType.BENEFIT_ELIGIBILITY,
            description="Active eligibility records for study kits, laptops, and textbooks.",
            visibility=Report.Visibility.ROLES,
            allowed_roles="SUPER_ADMIN,ADMIN,ACCOUNTANT",
            created_by=admin_user,
        )
        Report.objects.create(
            title="School Infrastructure & Partner Directory",
            report_type=Report.ReportType.SCHOOL_INFRASTRUCTURE,
            description="Government schools directory with headmaster contacts and regional reach.",
            visibility=Report.Visibility.PUBLIC,
            created_by=admin_user,
        )

    # Fetch and filter reports visible to this user
    all_reports = Report.objects.select_related("created_by").prefetch_related("allowed_groups").all()
    user_visible_reports = [r for r in all_reports if r.is_visible_to(request.user)]

    if type_filter:
        user_visible_reports = [r for r in user_visible_reports if r.report_type == type_filter]

    if status_filter:
        user_visible_reports = [r for r in user_visible_reports if r.status == status_filter]

    if scope_filter == "mine":
        user_visible_reports = [r for r in user_visible_reports if r.created_by_id == request.user.id]
    elif scope_filter == "public":
        user_visible_reports = [r for r in user_visible_reports if r.visibility == Report.Visibility.PUBLIC]
    elif scope_filter == "shared":
        user_visible_reports = [
            r for r in user_visible_reports
            if r.visibility in [Report.Visibility.ROLES, Report.Visibility.GROUPS]
        ]

    # -------------------------------------------------------------------------
    # ACTIVITY LOGS
    # -------------------------------------------------------------------------

    activity_logs = ActivityLog.objects.select_related("user").all()

    if category_filter:
        activity_logs = activity_logs.filter(category=category_filter)

    if action_type_filter:
        activity_logs = activity_logs.filter(action_type=action_type_filter)

    try:
        if date_from:
            parsed_date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            start_datetime = timezone.make_aware(
                datetime.combine(parsed_date_from, time.min)
            )
            activity_logs = activity_logs.filter(timestamp__gte=start_datetime)
    except ValueError:
        date_from = ""

    try:
        if date_to:
            parsed_date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            end_datetime = timezone.make_aware(
                datetime.combine(parsed_date_to + timedelta(days=1), time.min)
            )
            activity_logs = activity_logs.filter(timestamp__lt=end_datetime)
    except ValueError:
        date_to = ""

    # -------------------------------------------------------------------------
    # ELIGIBILITY / BENEFIT DATA
    # -------------------------------------------------------------------------

    eligibility_records = EligibilityRecord.objects.filter(eligible=True).select_related("student")

    if academic_year:
        eligibility_records = eligibility_records.filter(academic_year=academic_year)

    total_students = Student.objects.filter(status=Student.Status.ACTIVE).count()

    study_kit_count = eligibility_records.filter(benefit_type=BenefitType.STUDY_KIT).count()
    laptop_count = eligibility_records.filter(benefit_type=BenefitType.LAPTOP).count()
    book_count = eligibility_records.filter(benefit_type=BenefitType.BOOK).count()
    workbook_count = eligibility_records.filter(benefit_type=BenefitType.WORKBOOK).count()
    internship_count = eligibility_records.filter(benefit_type=BenefitType.INTERNSHIP).count()

    academic_years = (
        EligibilityRecord.objects.values_list("academic_year", flat=True)
        .distinct()
        .order_by("-academic_year")
    )

    can_create = can_edit_reports(request.user)
    form = ReportForm() if can_create else None

    all_roles = (
        User.get_all_role_choices()
        if hasattr(User, "get_all_role_choices")
        else getattr(User, "Role", {}).choices
    )
    all_groups = Group.objects.all().order_by("name")

    categories = [
        {"value": "STUDENT", "label": "Students"},
        {"value": "ACADEMIC", "label": "Academics"},
        {"value": "INVENTORY", "label": "Inventory"},
        {"value": "SCHOOL", "label": "Schools"},
        {"value": "EVENT", "label": "Events"},
        {"value": "DISTRIBUTION", "label": "Distributions"},
        {"value": "INTERNSHIP", "label": "Internships"},
        {"value": "VOLUNTEER", "label": "Volunteers"},
        {"value": "REPORT", "label": "Reports"},
        {"value": "AUTH", "label": "Authentication"},
    ]

    action_types = [
        {"value": "CREATE", "label": "Created"},
        {"value": "UPDATE", "label": "Updated"},
        {"value": "DELETE", "label": "Deleted"},
        {"value": "LOGIN", "label": "Logged In"},
        {"value": "LOGOUT", "label": "Logged Out"},
        {"value": "VIEW", "label": "Viewed"},
        {"value": "EXPORT", "label": "Exported"},
        {"value": "IMPORT", "label": "Imported"},
        {"value": "OTHER", "label": "Other"},
    ]

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
        # Reports Hub Context
        "reports": user_visible_reports,
        "can_create_reports": can_create,
        "form": form,
        "type_filter": type_filter,
        "scope_filter": scope_filter,
        "status_filter": status_filter,
        "report_types": Report.ReportType.choices,
        "report_statuses": Report.Status.choices,
        "available_roles": all_roles,
        "available_groups": all_groups,
    }

    return render(request, "reports/list.html", context)


# =============================================================================
# REPORT CREATE
# =============================================================================

def report_create(request):
    """
    Create a new Report definition. Restricted to users with edit access.
    Supports standard POST and AJAX JSON.
    """
    if not can_edit_reports(request.user):
        raise PermissionDenied("You do not have permission to create reports.")

    if request.method == "POST":
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(user=request.user)
            log_activity(
                request.user,
                f"Created Report '{report.title}' ({report.get_access_display()})",
                "REPORT",
                f"Type: {report.get_report_type_display()}, Status: {report.get_status_display()}, Visibility: {report.get_access_display()}",
            )

            is_ajax = (
                request.headers.get("x-requested-with") == "XMLHttpRequest"
                or request.headers.get("accept") == "application/json"
            )
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "report_id": report.id,
                    "title": report.title,
                    "access": report.get_access_display(),
                    "redirect_url": f"/reports/{report.id}/",
                })

            messages.success(request, f"Report '{report.title}' created successfully.")
            return redirect("reports:detail", pk=report.pk)
        else:
            is_ajax = (
                request.headers.get("x-requested-with") == "XMLHttpRequest"
                or request.headers.get("accept") == "application/json"
            )
            if is_ajax:
                errors = {k: [str(e) for e in errs] for k, errs in form.errors.items()}
                return JsonResponse({"success": False, "errors": errors}, status=400)
    else:
        form = ReportForm()

    all_roles = (
        User.get_all_role_choices()
        if hasattr(User, "get_all_role_choices")
        else getattr(User, "Role", {}).choices
    )
    all_groups = Group.objects.all().order_by("name")

    return render(
        request,
        "reports/form.html",
        {
            "form": form,
            "action": "Create",
            "available_roles": all_roles,
            "available_groups": all_groups,
        },
    )


# =============================================================================
# REPORT DETAIL
# =============================================================================

def report_detail(request, pk):
    """
    View report details, aggregated metrics, data table, and export options.
    Restricted to users who have access according to report visibility rules.
    """
    report = get_object_or_404(
        Report.objects.select_related("created_by").prefetch_related("allowed_groups"),
        pk=pk,
    )

    if not report.is_visible_to(request.user):
        raise PermissionDenied("You do not have access to view this report.")

    data = report.generate_data()
    can_manage = can_edit_reports(request.user) and (
        report.created_by_id == request.user.id
        or getattr(request.user, "is_admin", False)
        or getattr(request.user, "is_superuser", False)
    )

    return render(
        request,
        "reports/detail.html",
        {
            "report": report,
            "data": data,
            "can_manage": can_manage,
        },
    )


# =============================================================================
# REPORT EDIT
# =============================================================================

def report_edit(request, pk):
    """
    Edit an existing report definition. Restricted to creator or admin.
    """
    report = get_object_or_404(Report, pk=pk)

    can_manage = can_edit_reports(request.user) and (
        report.created_by_id == request.user.id
        or getattr(request.user, "is_admin", False)
        or getattr(request.user, "is_superuser", False)
    )
    if not can_manage:
        raise PermissionDenied("You do not have permission to edit this report.")

    if request.method == "POST":
        form = ReportForm(request.POST, request.FILES, instance=report)
        if form.is_valid():
            report = form.save()
            log_activity(
                request.user,
                f"Updated Report '{report.title}'",
                "REPORT",
                f"Type: {report.get_report_type_display()}, Status: {report.get_status_display()}, Visibility: {report.get_access_display()}",
            )
            messages.success(request, f"Report '{report.title}' updated successfully.")
            return redirect("reports:detail", pk=report.pk)
    else:
        form = ReportForm(instance=report)

    all_roles = (
        User.get_all_role_choices()
        if hasattr(User, "get_all_role_choices")
        else getattr(User, "Role", {}).choices
    )
    all_groups = Group.objects.all().order_by("name")

    return render(
        request,
        "reports/form.html",
        {
            "form": form,
            "report": report,
            "action": "Edit",
            "available_roles": all_roles,
            "available_groups": all_groups,
        },
    )


# =============================================================================
# REPORT DELETE
# =============================================================================

def report_delete(request, pk):
    """
    Delete an existing report definition.
    """
    report = get_object_or_404(Report, pk=pk)

    can_manage = can_edit_reports(request.user) and (
        report.created_by_id == request.user.id
        or getattr(request.user, "is_admin", False)
        or getattr(request.user, "is_superuser", False)
    )
    if not can_manage:
        raise PermissionDenied("You do not have permission to delete this report.")

    if request.method == "POST":
        title = report.title
        report.delete()
        log_activity(request.user, f"Deleted Report '{title}'", "REPORT")
        messages.success(request, f"Report '{title}' deleted successfully.")
        return redirect("reports:list")

    return redirect("reports:detail", pk=report.pk)


# =============================================================================
# REPORT EXPORTS
# =============================================================================

def report_export_csv(request, pk):
    """
    Stream a CSV export of the report data.
    """
    report = get_object_or_404(Report, pk=pk)

    if not report.is_visible_to(request.user):
        raise PermissionDenied("You do not have access to view this report.")

    data = report.generate_data()

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = f"{report.title.lower().replace(' ', '_')}_{report.pk}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([f"Report: {report.title}"])
    writer.writerow([f"Type: {report.get_report_type_display()}"])
    writer.writerow([f"Access: {report.get_access_display()}"])
    writer.writerow([])

    writer.writerow(data["headers"])

    for row in data["rows"]:
        writer.writerow(row)

    return response


def report_export_excel(request, pk):
    """
    Stream an Excel (.xlsx) export of the report data using openpyxl.
    """
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    report = get_object_or_404(Report, pk=pk)
    if not report.is_visible_to(request.user):
        raise PermissionDenied("You do not have access to view this report.")

    data = report.generate_data()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report Data"

    title_font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    meta_font = Font(name="Calibri", size=10, italic=True, color="64748B")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="DD2D27", end_color="DD2D27", fill_type="solid")
    border_side = Side(border_style="thin", color="E2E8F0")
    cell_border = Border(top=border_side, bottom=border_side, left=border_side, right=border_side)

    ws.append([report.title])
    ws.cell(row=1, column=1).font = title_font

    ws.append([
        f"Report Type: {report.get_report_type_display()} | Status: {report.get_status_display()} | Visibility: {report.get_access_display()}"
    ])
    ws.cell(row=2, column=1).font = meta_font

    if report.academic_year or report.category_filter:
        ws.append([f"Academic Year: {report.academic_year or 'All'} | Filter: {report.category_filter or 'None'}"])
        ws.cell(row=3, column=1).font = meta_font

    ws.append([])

    headers = data.get("headers", [])
    ws.append(headers)
    header_row_idx = ws.max_row
    for col_idx in range(1, len(headers) + 1):
        c = ws.cell(row=header_row_idx, column=col_idx)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center" if "Status" in headers[col_idx-1] or "ID" in headers[col_idx-1] else "left")

    for row in data.get("rows", []):
        ws.append(row)
        curr_row = ws.max_row
        for col_idx in range(1, len(row) + 1):
            c = ws.cell(row=curr_row, column=col_idx)
            c.border = cell_border

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    filename = f"{report.title.lower().replace(' ', '_')}_{report.pk}.xlsx"
    response = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# =============================================================================
# ACTIVITY LOG API
# =============================================================================

def api_activity_logs(request):
    """
    Returns the latest activity logs as JSON.
    """
    category_filter = request.GET.get("category", "").strip().upper()
    action_type_filter = request.GET.get("action_type", "").strip().upper()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    logs = ActivityLog.objects.select_related("user").all()

    if category_filter:
        logs = logs.filter(category=category_filter)

    if action_type_filter:
        logs = logs.filter(action_type=action_type_filter)

    try:
        if date_from:
            parsed_date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            start_datetime = timezone.make_aware(
                datetime.combine(parsed_date_from, time.min)
            )
            logs = logs.filter(timestamp__gte=start_datetime)
    except ValueError:
        date_from = ""

    try:
        if date_to:
            parsed_date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            end_datetime = timezone.make_aware(
                datetime.combine(parsed_date_to + timedelta(days=1), time.min)
            )
            logs = logs.filter(timestamp__lt=end_datetime)
    except ValueError:
        date_to = ""

    data = []
    for log in logs[:100]:
        username = log.user.username if log.user else "System"
        data.append({
            "id": log.id,
            "timestamp": log.timestamp.strftime("%b %d, %Y %H:%M:%S"),
            "category": log.category or "GENERAL",
            "action_type": log.action_type or "OTHER",
            "action": log.action or "",
            "username": username,
            "performed_by": username,
            "object_type": log.object_type or "",
            "object_id": log.object_id or "",
            "details": log.details or "",
        })

    return JsonResponse({
        "success": True,
        "logs": data,
        "count": len(data),
    })
