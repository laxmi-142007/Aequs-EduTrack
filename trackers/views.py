import csv
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.views.decorators.http import require_POST
from programs.models import NGO
from trackers.models import WeeklyTrackerSession, SchoolEnrollment, Programme
from trackers.filters import WeeklyTrackerSessionFilter
from trackers.services.excel_importer import import_yfs_workbook


def get_current_ngo(ngo_slug):
    """
    Resolves requested NGO from URL slug (yfs, agastya, pratham).
    Defaults to Youth for Seva (YFS).
    """
    slug = (ngo_slug or "yfs").strip().lower()
    slug_map = {
        "yfs": "YFS",
        "youth-for-seva": "YFS",
        "agastya": "AGASTYA",
        "pratham": "PRATHAM",
    }
    code = slug_map.get(slug, slug.upper())
    ngo = NGO.objects.filter(code__iexact=code).first()
    if not ngo:
        ngo = NGO.objects.filter(code="YFS").first()
    if not ngo:
        ngo = NGO.objects.create(name="Youth for Seva", code="YFS")
    return ngo


def get_ngo_nav(current_ngo):
    """
    Builds the top navigation switcher for partner NGO modules.
    Keeps each organization's data strictly separated.
    """
    core_definitions = [
        {
            "code": "YFS",
            "slug": "yfs",
            "name": "Youth for Seva (YFS)",
            "short_name": "Youth for Seva",
            "badge": "🟡",
            "color": "#f59e0b",
            "border": "#d97706",
            "bg_light": "#fef3c7",
        },
        {
            "code": "AGASTYA",
            "slug": "agastya",
            "name": "Agastya International Foundation",
            "short_name": "Agastya",
            "badge": "🔵",
            "color": "#2563eb",
            "border": "#1d4ed8",
            "bg_light": "#dbeafe",
        },
        {
            "code": "PRATHAM",
            "slug": "pratham",
            "name": "Pratham Foundation",
            "short_name": "Pratham",
            "badge": "🔴",
            "color": "#dc2626",
            "border": "#b91c1c",
            "bg_light": "#fee2e2",
        },
    ]

    ngo_nav = []
    for item in core_definitions:
        ngo_obj = NGO.objects.filter(code=item["code"]).first()
        sess_count = WeeklyTrackerSession.objects.filter(ngo__code=item["code"]).count()
        enr_count = SchoolEnrollment.objects.filter(ngo__code=item["code"]).count()
        sch_count = ngo_obj.partner_schools.count() if ngo_obj else 0

        is_active = (current_ngo and current_ngo.code == item["code"])
        ngo_nav.append({
            "code": item["code"],
            "slug": item["slug"],
            "name": item["name"],
            "short_name": item["short_name"],
            "badge": item["badge"],
            "color": item["color"],
            "border": item["border"],
            "bg_light": item["bg_light"],
            "session_count": sess_count,
            "enrollment_count": enr_count,
            "school_count": sch_count,
            "is_active": is_active,
            "school_url": f"/schools/{item['slug']}/",
            "session_url": reverse("trackers:ngo_session_list", args=[item["slug"]]),
            "enrollment_url": reverse("trackers:ngo_enrollment_list", args=[item["slug"]]),
            "dossier_url": reverse("programs:ngo_detail", args=[ngo_obj.id]) if ngo_obj else reverse("programs:ngo_list"),
        })
    return ngo_nav


def session_list_view(request, ngo_slug="yfs"):
    """
    Main CRM view for Weekly Tracker Sessions with NGO-wise separation,
    dynamic filtering, multi-column sorting, live KPI aggregation, and upload modal.
    """
    current_ngo = get_current_ngo(ngo_slug)
    ngo_nav = get_ngo_nav(current_ngo)

    # Base queryset strictly scoped to this NGO
    base_qs = WeeklyTrackerSession.objects.filter(ngo=current_ngo).select_related("school", "ngo")

    # Apply django-filter scoped to current NGO
    session_filter = WeeklyTrackerSessionFilter(request.GET, queryset=base_qs, current_ngo=current_ngo)
    filtered_qs = session_filter.qs

    # Sorting resolution: handle both sort_by and order_by parameters
    sort_by = request.GET.get("sort_by") or request.GET.get("order_by") or "-session_date"
    sort_fields_map = {
        "date": "session_date",
        "-date": "-session_date",
        "session_date": "session_date",
        "-session_date": "-session_date",
        "school": "school__name",
        "-school": "-school__name",
        "school__name": "school__name",
        "-school__name": "-school__name",
        "programme": "programme",
        "-programme": "-programme",
        "instructor": "instructor_name",
        "-instructor": "-instructor_name",
        "instructor_name": "instructor_name",
        "-instructor_name": "-instructor_name",
        "exposures": "total_exposures",
        "-exposures": "-total_exposures",
        "total_exposures": "total_exposures",
        "-total_exposures": "-total_exposures",
        "boys": "boys_present",
        "-boys": "-boys_present",
        "boys_present": "boys_present",
        "-boys_present": "-boys_present",
        "girls": "girls_present",
        "-girls": "-girls_present",
        "girls_present": "girls_present",
        "-girls_present": "-girls_present",
    }
    actual_sort = sort_fields_map.get(sort_by, "-session_date")
    filtered_qs = filtered_qs.order_by(actual_sort, "-id")

    # Dynamic KPI Aggregation based strictly on active filtered queryset for this NGO
    kpis = filtered_qs.aggregate(
        total_boys=Sum("boys_present"),
        total_girls=Sum("girls_present"),
        total_exposures=Sum("total_exposures"),
    )
    total_sessions = filtered_qs.count()
    total_boys = kpis["total_boys"] or 0
    total_girls = kpis["total_girls"] or 0
    total_exposures = kpis["total_exposures"] or 0

    active_schools_count = (
        filtered_qs.exclude(school__isnull=True)
        .values("school")
        .distinct()
        .count()
    )
    active_instructors_count = (
        filtered_qs.exclude(instructor_name="")
        .values("instructor_name")
        .distinct()
        .count()
    )

    # Scoped programmes for this NGO
    if current_ngo.code == "YFS":
        available_programmes = [
            ("CHAAP_JR", "CHAAP Junior (HHP)"),
            ("CHAAP_YUVA", "CHAAP-Yuva (AHAP)"),
            ("SEP", "Student Excel Program (SEP)"),
            ("IGNITE_BGM", "IGNITE Belagavi"),
            ("IGNITE_HBL", "IGNITE Hubballi"),
            ("NMMS", "NMMS Training"),
            ("CAMP", "Winter & Summer Camp"),
            ("SAP", "Student Activity Program (SAP)"),
            ("OTHERS", "Other Programmes"),
        ]
    elif current_ngo.code == "AGASTYA":
        available_programmes = [
            ("MSL", "Mobile Science Lab (MSL)"),
            ("AVISHKAR", "Avishkar Science Fair"),
            ("VASANTHA", "Vasantha After-School"),
            ("YUVACHARYA", "Yuvacharya B.Ed Training"),
            ("OTHERS", "Other Programmes"),
        ]
    elif current_ngo.code == "PRATHAM":
        available_programmes = [
            ("OPN", "One Notebook Program"),
            ("READING", "Learning & Reading Camp"),
            ("OTHERS", "Other Programmes"),
        ]
    else:
        available_programmes = Programme.choices

    # Pagination (50 rows per page)
    paginator = Paginator(filtered_qs, 50)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Build clean query string for pagination links preserving filters
    query_params = request.GET.copy()
    if "page" in query_params:
        del query_params["page"]
    base_query_string = query_params.urlencode()

    context = {
        "current_ngo": current_ngo,
        "requested_ngo": current_ngo.code.lower(),
        "ngo_nav": ngo_nav,
        "filter": session_filter,
        "page_obj": page_obj,
        "sessions": page_obj.object_list,
        "total_sessions": total_sessions,
        "total_boys": total_boys,
        "total_girls": total_girls,
        "total_exposures": total_exposures,
        "active_schools_count": active_schools_count,
        "active_instructors_count": active_instructors_count,
        "current_sort": sort_by,
        "base_query_string": base_query_string,
        "programmes": available_programmes,
        "academic_years": ["2025-26", "2026-27"],
        "active_page": f"trackers_{current_ngo.code.lower()}",
        "foundation_subtab": "trackers",
    }
    return render(request, "trackers/session_list.html", context)


def upload_tracker_view(request, ngo_slug="yfs"):
    """
    Handles Excel tracker upload (.xlsx) from modal or dedicated upload page,
    scoped strictly to the selected partner NGO module.
    """
    current_ngo = get_current_ngo(ngo_slug)

    if request.method != "POST":
        ngo_nav = get_ngo_nav(current_ngo)
        return render(
            request,
            "trackers/upload_modal.html",
            {
                "current_ngo": current_ngo,
                "requested_ngo": current_ngo.code.lower(),
                "ngo_nav": ngo_nav,
                "foundation_subtab": "trackers",
            },
        )

    uploaded_file = request.FILES.get("file")
    academic_year = request.POST.get("academic_year", "").strip()
    target_ngo_code = request.POST.get("ngo_code", current_ngo.code).strip()

    if not uploaded_file:
        messages.error(request, "Please select an Excel (.xlsx) file to upload.")
        return redirect("trackers:ngo_session_list", current_ngo.code.lower())

    if not uploaded_file.name.lower().endswith((".xlsx", ".xls")):
        messages.error(request, "Only Microsoft Excel (.xlsx/.xls) files are supported.")
        return redirect("trackers:ngo_session_list", current_ngo.code.lower())

    if not academic_year:
        if "2025-26" in uploaded_file.name:
            academic_year = "2025-26"
        elif "2026-27" in uploaded_file.name:
            academic_year = "2026-27"
        else:
            academic_year = "2025-26"

    try:
        res = import_yfs_workbook(uploaded_file, academic_year, ngo_code=target_ngo_code)
        msg = (
            f"Successfully imported {academic_year} tracker for {current_ngo.name}: "
            f"{res['sessions_imported']:,} sessions, {res['enrollments_imported']:,} class enrollments, "
            f"{res['total_exposures']:,} exposures across {res['schools_count']} schools."
        )
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "success", "message": msg, "data": res})

        messages.success(request, msg)
    except Exception as e:
        err_msg = f"Failed to ingest Excel workbook: {e}"
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "message": err_msg}, status=400)
        messages.error(request, err_msg)

    redirect_url = reverse("trackers:ngo_session_list", args=[current_ngo.code.lower()])
    return redirect(f"{redirect_url}?academic_year={academic_year}")


def enrollment_list_view(request, ngo_slug="yfs"):
    """
    Displays normalized school standard enrollment counts for the selected NGO module.
    """
    current_ngo = get_current_ngo(ngo_slug)
    ngo_nav = get_ngo_nav(current_ngo)

    ay = request.GET.get("academic_year", "").strip()
    prog = request.GET.get("programme", "").strip()
    search = request.GET.get("q", "").strip()

    # Queryset strictly scoped to current NGO
    qs = SchoolEnrollment.objects.filter(ngo=current_ngo).select_related("school", "ngo")
    if ay:
        qs = qs.filter(academic_year=ay)
    if prog:
        qs = qs.filter(programme=prog)
    if search:
        qs = qs.filter(Q(school__name__icontains=search) | Q(standard__icontains=search))

    totals = qs.aggregate(
        b=Sum("boys"),
        g=Sum("girls"),
        t=Sum("total"),
    )

    if current_ngo.code == "YFS":
        available_programmes = [
            ("CHAAP_JR", "CHAAP Junior (HHP)"),
            ("CHAAP_YUVA", "CHAAP-Yuva (AHAP)"),
            ("SEP", "Student Excel Program (SEP)"),
            ("IGNITE_BGM", "IGNITE Belagavi"),
            ("IGNITE_HBL", "IGNITE Hubballi"),
            ("NMMS", "NMMS Training"),
            ("CAMP", "Winter & Summer Camp"),
            ("SAP", "Student Activity Program (SAP)"),
            ("OTHERS", "Other Programmes"),
        ]
    elif current_ngo.code == "AGASTYA":
        available_programmes = [
            ("MSL", "Mobile Science Lab (MSL)"),
            ("AVISHKAR", "Avishkar Science Fair"),
            ("VASANTHA", "Vasantha After-School"),
            ("YUVACHARYA", "Yuvacharya B.Ed Training"),
            ("OTHERS", "Other Programmes"),
        ]
    elif current_ngo.code == "PRATHAM":
        available_programmes = [
            ("OPN", "One Notebook Program"),
            ("READING", "Learning & Reading Camp"),
            ("OTHERS", "Other Programmes"),
        ]
    else:
        available_programmes = Programme.choices

    from trackers.roster import get_ngo_enrollment_roster
    roster_data = get_ngo_enrollment_roster(
        current_ngo,
        academic_year=ay or "2025-26",
        programme=prog,
        search=search,
    )

    paginator = Paginator(qs, 60)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "trackers/enrollment_list.html",
        {
            "current_ngo": current_ngo,
            "requested_ngo": current_ngo.code.lower(),
            "ngo_nav": ngo_nav,
            "roster_data": roster_data,
            "page_obj": page_obj,
            "enrollments": page_obj.object_list,
            "total_boys": totals["b"] or 0,
            "total_girls": totals["g"] or 0,
            "total_students": totals["t"] or 0,
            "selected_ay": ay or "2025-26",
            "selected_prog": prog,
            "search_q": search,
            "programmes": available_programmes,
            "academic_years": ["2025-26", "2026-27"],
            "active_page": f"trackers_enrollments_{current_ngo.code.lower()}",
            "foundation_subtab": "enrollments",
        },
    )


def export_sessions_csv(request, ngo_slug="yfs"):
    """
    Exports filtered weekly tracker sessions for the selected NGO as a CSV file.
    """
    current_ngo = get_current_ngo(ngo_slug)
    base_qs = WeeklyTrackerSession.objects.filter(ngo=current_ngo).select_related("school", "ngo")
    session_filter = WeeklyTrackerSessionFilter(request.GET, queryset=base_qs, current_ngo=current_ngo)
    qs = session_filter.qs.order_by("-session_date", "-id")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{current_ngo.code}_Weekly_Tracker_Sessions.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "NGO Partner",
        "Academic Year",
        "Programme",
        "Session Date",
        "Month",
        "Day",
        "School Name",
        "Raw Location/Activity",
        "Standard",
        "Division",
        "Timing",
        "Topic",
        "Instructor Name",
        "Session Type",
        "Boys Present",
        "Girls Present",
        "Total Exposures",
        "Teacher Present",
    ])

    for s in qs[:5000]:
        writer.writerow([
            current_ngo.name,
            s.academic_year,
            s.get_programme_display(),
            s.session_date.strftime("%Y-%m-%d") if s.session_date else "",
            s.month_name,
            s.day_number or "",
            s.school.name if s.school else "",
            s.raw_location_or_activity,
            s.standard,
            s.division,
            s.timing,
            s.topic,
            s.instructor_name,
            s.session_type,
            s.boys_present,
            s.girls_present,
            s.total_exposures,
            "Yes" if s.teacher_present else "No",
        ])

    return response
