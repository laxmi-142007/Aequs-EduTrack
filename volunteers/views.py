import csv
from decimal import Decimal
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.db.models.functions import Coalesce

from .models import (
    Volunteer,
    VolunteerActivity,
    EventParticipation,
    VolunteerFormLink,
    EmployeeTestimonial,
)
from events.models import Event
from programs.metrics import get_volunteering_kpis


def volunteer_list(request):
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    gender_filter = request.GET.get("gender", "").strip()
    selected_ay = request.GET.get("ay", "2026-27").strip()

    volunteers = Volunteer.objects.all()

    # KPI counts across all volunteers
    total_volunteers = volunteers.count()
    active_count = volunteers.filter(status="ACTIVE").count()
    total_hours_aggregated = EventParticipation.objects.aggregate(Sum("hours_contributed"))["hours_contributed__sum"] or 0
    total_participations = EventParticipation.objects.count()

    # Excel Spec: Current Year vs Historical Volunteering metrics
    vol_curr = get_volunteering_kpis(academic_year="2026-27")
    vol_hist = get_volunteering_kpis(academic_year="all")

    if q:
        volunteers = volunteers.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q) |
            Q(skills__icontains=q) |
            Q(occupation__icontains=q) |
            Q(city__icontains=q)
        )

    if status_filter:
        volunteers = volunteers.filter(status=status_filter)

    if gender_filter:
        volunteers = volunteers.filter(gender=gender_filter)

    # Annotate with participation count and contributed hours
    volunteers = volunteers.annotate(
        total_hours=Sum("event_participations__hours_contributed"),
        event_count=Count("event_participations"),
    )

    # Top 10 Volunteers Leaderboard filtered by selected Academic Year
    part_filter = Q()
    if selected_ay != "all":
        year_prefix = selected_ay.split("-")[0] if "-" in selected_ay else selected_ay
        part_filter = Q(event_participations__event__event_date__year=year_prefix) | Q(event_participations__assigned_at__year=year_prefix)

    top_volunteers_qs = (
        Volunteer.objects.annotate(
            total_hours=Coalesce(Sum("event_participations__hours_contributed", filter=part_filter), Decimal("0.0")),
            events_count=Count("event_participations", filter=part_filter, distinct=True),
        )
        .filter(status="ACTIVE")
        .order_by("-total_hours", "-events_count", "first_name")[:10]
    )

    top_volunteers = list(top_volunteers_qs)
    for idx, tv in enumerate(top_volunteers, 1):
        tv.leaderboard_rank = idx
        th = float(tv.total_hours or 0)
        if th >= 30:
            tv.tier_name = "Champion"
            tv.tier_badge = "🏆 Champion"
            tv.tier_color = "#7c3aed"
            tv.tier_bg = "#f5f3ff"
        elif th >= 20:
            tv.tier_name = "Gold"
            tv.tier_badge = "🥇 Gold"
            tv.tier_color = "#b45309"
            tv.tier_bg = "#fef3c7"
        elif th >= 10:
            tv.tier_name = "Silver"
            tv.tier_badge = "🥈 Silver"
            tv.tier_color = "#475569"
            tv.tier_bg = "#f1f5f9"
        else:
            tv.tier_name = "Bronze"
            tv.tier_badge = "🥉 Bronze"
            tv.tier_color = "#c2410c"
            tv.tier_bg = "#ffedd5"

    # Excel Spec: Activities Pipeline for the year (Completed, Ongoing, Upcoming)
    completed_activities = VolunteerActivity.objects.filter(status="COMPLETED").select_related("volunteer")
    ongoing_activities = VolunteerActivity.objects.filter(status="ONGOING").select_related("volunteer")
    upcoming_activities = VolunteerActivity.objects.filter(status="ASSIGNED").select_related("volunteer")

    # Excel Spec: Employee Testimonials with Video
    testimonials = EmployeeTestimonial.objects.all()

    # Get or generate active unique form link
    form_link = VolunteerFormLink.objects.filter(is_active=True).order_by("-created_at").first()
    if not form_link:
        form_link = VolunteerFormLink.objects.create()
    form_url = request.build_absolute_uri(f"/volunteers/form/{form_link.token}/")
    qr_url = request.build_absolute_uri(f"/volunteers/form/qr/{form_link.token}/")

    academic_years = [
        ("2026-27", "Current Year (2026-27)"),
        ("2025-26", "Academic Year 2025-26"),
        ("2024-25", "Academic Year 2024-25"),
        ("all", "All Years (Consolidated)"),
    ]

    return render(
        request,
        "volunteers/volunteer_list.html",
        {
            "volunteers": volunteers,
            "top_volunteers": top_volunteers,
            "q": q,
            "status_filter": status_filter,
            "gender_filter": gender_filter,
            "selected_ay": selected_ay,
            "academic_years": academic_years,
            "status_choices": Volunteer.STATUS_CHOICES,
            "gender_choices": Volunteer.GENDER_CHOICES,
            "total_volunteers": total_volunteers,
            "active_count": active_count,
            "total_hours": round(total_hours_aggregated, 1),
            "total_participations": total_participations,
            "vol_curr": vol_curr,
            "vol_hist": vol_hist,
            "completed_activities": completed_activities,
            "ongoing_activities": ongoing_activities,
            "upcoming_activities": upcoming_activities,
            "testimonials": testimonials,
            "form_link": form_link,
            "form_url": form_url,
            "qr_url": qr_url,
            "upcoming_events": Event.objects.all().order_by("-event_date"),
        },
    )


def _build_volunteer_journey_dict(vol):
    """Helper to structure volunteer profile, stats, and chronological timeline for Journey display."""
    participations_qs = vol.event_participations.select_related("event").order_by("-event__event_date", "-assigned_at")
    total_hours = participations_qs.aggregate(total=Sum("hours_contributed"))["total"] or Decimal("0.0")
    events_count = participations_qs.count()

    activities_qs = vol.activities.order_by("-activity_date")
    activities_count = activities_qs.count()

    th = float(total_hours)
    if th >= 30:
        tier = "Champion"
        tier_color = "#7c3aed"
        tier_bg = "#f3e8ff"
    elif th >= 20:
        tier = "Gold"
        tier_color = "#b45309"
        tier_bg = "#fef3c7"
    elif th >= 10:
        tier = "Silver"
        tier_color = "#475569"
        tier_bg = "#f1f5f9"
    else:
        tier = "Bronze"
        tier_color = "#c2410c"
        tier_bg = "#ffedd5"

    timeline = []
    for p in participations_qs:
        ev = p.event
        timeline.append({
            "type": "event",
            "title": ev.title if ev else "CSR Drive",
            "date": ev.event_date.strftime("%d %b %Y") if ev and ev.event_date else (p.assigned_at.strftime("%d %b %Y") if p.assigned_at else "N/A"),
            "location": (ev.location if ev else "") or "Belagavi Campus",
            "role": p.role or "Volunteer",
            "hours": float(p.hours_contributed or 0),
            "status": p.get_participation_status_display(),
            "status_code": p.participation_status,
        })

    for act in activities_qs:
        timeline.append({
            "type": "activity",
            "title": act.activity_name,
            "date": act.activity_date.strftime("%d %b %Y") if act.activity_date else "N/A",
            "location": vol.plant_location or "Belagavi SEZ",
            "role": "Community Task",
            "hours": 0.0,
            "status": act.get_status_display(),
            "status_code": act.status,
            "description": act.description,
        })

    return {
        "id": vol.id,
        "name": f"{vol.first_name} {vol.last_name}".strip(),
        "employee_code": vol.employee_code or "—",
        "email": vol.email,
        "phone": vol.phone,
        "department": vol.department or "Aerospace Operations",
        "plant_location": vol.plant_location or "Belagavi SEZ",
        "academic_year": vol.academic_year or "2026-27",
        "status": vol.status,
        "tier": tier,
        "tier_color": tier_color,
        "tier_bg": tier_bg,
        "total_hours": th,
        "events_count": events_count,
        "activities_count": activities_count,
        "profile_url": f"/volunteers/{vol.id}/",
        "timeline": timeline,
    }


def journey_lookup(request):
    """Lookup volunteer journey by employee ID / code, email, or name."""
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"success": False, "message": "Please enter an Employee ID or Name to search."}, status=400)

    # Search leniently: exact code, contains code, email, or full name
    vol = (
        Volunteer.objects.filter(employee_code__iexact=query).first()
        or Volunteer.objects.filter(employee_code__icontains=query).first()
        or Volunteer.objects.filter(email__iexact=query).first()
        or Volunteer.objects.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).first()
    )

    if not vol:
        return JsonResponse({
            "success": False,
            "message": f"No employee volunteer found matching '{query}'. Please verify your Employee ID (e.g. AEQ-1001) or enroll as a new volunteer."
        }, status=404)

    return JsonResponse({
        "success": True,
        "volunteer": _build_volunteer_journey_dict(vol)
    })


def journey_lookup_by_pk(request, pk):
    """Lookup volunteer journey by primary key."""
    vol = get_object_or_404(Volunteer, pk=pk)
    return JsonResponse({
        "success": True,
        "volunteer": _build_volunteer_journey_dict(vol)
    })


def testimonial_create(request):
    """View to submit a new employee volunteer video testimonial."""
    if request.method == "POST":
        name = request.POST.get("employee_name", "").strip()
        role = request.POST.get("employee_role", "").strip()
        dept = request.POST.get("department", "").strip()
        loc = request.POST.get("plant_location", "Belagavi SEZ").strip()
        quote = request.POST.get("quote", "").strip()
        url = request.POST.get("video_url", "").strip()
        ay = request.POST.get("academic_year", "2026-27").strip()

        if name and quote:
            EmployeeTestimonial.objects.create(
                employee_name=name,
                employee_role=role,
                department=dept,
                plant_location=loc,
                quote=quote,
                video_url=url,
                academic_year=ay,
            )
            messages.success(request, f"Employee testimonial from {name} added successfully!")
        else:
            messages.error(request, "Please enter both employee name and reflection quote.")
    return redirect("volunteers:list")


AEQUS_DEPARTMENTS = [
    "Aerospace Operations",
    "Aerospace Machining",
    "Assembly & Integration",
    "Quality Assurance & Inspection",
    "Special Processing / Surface Treatment",
    "Engineering & Design",
    "Supply Chain & Logistics",
    "Human Resources (HR)",
    "Finance & Accounts",
    "Information Technology (IT)",
    "Corporate Social Responsibility (CSR)",
    "Facilities & Maintenance",
    "Production Planning & Control (PPC)",
]

AEQUS_PLANTS = [
    "Belagavi SEZ (Main Aerospace Hub)",
    "Belagavi Unit 2 (Precision Machining)",
    "Hubballi Technology Centre",
    "Koppal Toy Manufacturing Cluster",
    "Bengaluru Corporate Office",
]

AEQUS_ACADEMIC_YEARS = [
    "2026-27",
    "2025-26",
    "2024-25",
]


def volunteer_create(request):
    errors = []
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not first_name:
            errors.append("First name is required.")
        if not email:
            errors.append("Email address is required.")
        elif Volunteer.objects.filter(email__iexact=email).exists():
            errors.append(f"A volunteer with email '{email}' is already enrolled.")
        if not phone:
            errors.append("Phone number is required.")

        if not errors:
            volunteer = Volunteer.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                employee_code=request.POST.get("employee_code", "").strip(),
                department=request.POST.get("department", "Aerospace Operations").strip(),
                plant_location=request.POST.get("plant_location", "Belagavi SEZ").strip(),
                academic_year=request.POST.get("academic_year", "2026-27").strip(),
                is_employee=request.POST.get("is_employee") in ["on", "true", "1", True],
                gender=request.POST.get("gender", ""),
                date_of_birth=request.POST.get("date_of_birth") or None,
                address=request.POST.get("address", ""),
                city=request.POST.get("city", ""),
                state=request.POST.get("state", ""),
                pincode=request.POST.get("pincode", ""),
                occupation=request.POST.get("occupation", ""),
                qualification=request.POST.get("qualification", ""),
                skills=request.POST.get("skills", ""),
                status=request.POST.get("status", "ACTIVE"),
                remarks=request.POST.get("remarks", ""),
            )

            messages.success(request, f"Employee Volunteer {volunteer.first_name} {volunteer.last_name} enrolled successfully in AEQATRA.")
            return redirect("volunteers:detail", pk=volunteer.pk)

    return render(
        request,
        "volunteers/volunteer_form.html",
        {
            "errors": errors,
            "form_data": request.POST if request.method == "POST" else None,
            "gender_choices": Volunteer.GENDER_CHOICES,
            "status_choices": Volunteer.STATUS_CHOICES,
            "departments": AEQUS_DEPARTMENTS,
            "plants": AEQUS_PLANTS,
            "academic_years": AEQUS_ACADEMIC_YEARS,
            "active_page": "volunteers",
        },
    )


def volunteer_detail(request, pk):
    volunteer = get_object_or_404(Volunteer, pk=pk)

    activities = volunteer.activities.all()
    participations = volunteer.event_participations.select_related("event").all()

    total_hours = participations.aggregate(Sum("hours_contributed"))["hours_contributed__sum"] or 0
    assigned_event_ids = participations.values_list("event_id", flat=True)
    available_events = Event.objects.exclude(id__in=assigned_event_ids)

    return render(
        request,
        "volunteers/volunteer_detail.html",
        {
            "volunteer": volunteer,
            "activities": activities,
            "participations": participations,
            "total_hours": round(total_hours, 1),
            "events_count": participations.count(),
            "activities_count": activities.count(),
            "available_events": available_events,
            "participation_status_choices": EventParticipation.STATUS_CHOICES,
            "activity_status_choices": VolunteerActivity.STATUS_CHOICES,
        },
    )


def volunteer_edit(request, pk):
    volunteer = get_object_or_404(Volunteer, pk=pk)
    errors = []

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not first_name:
            errors.append("First name is required.")
        if not email:
            errors.append("Email address is required.")
        elif Volunteer.objects.filter(email__iexact=email).exclude(pk=volunteer.pk).exists():
            errors.append(f"A volunteer with email '{email}' already exists.")
        if not phone:
            errors.append("Phone number is required.")

        if not errors:
            volunteer.first_name = first_name
            volunteer.last_name = request.POST.get("last_name", "").strip()
            volunteer.email = email
            volunteer.phone = phone
            volunteer.employee_code = request.POST.get("employee_code", "").strip()
            volunteer.department = request.POST.get("department", volunteer.department).strip()
            volunteer.plant_location = request.POST.get("plant_location", volunteer.plant_location).strip()
            volunteer.academic_year = request.POST.get("academic_year", volunteer.academic_year).strip()
            volunteer.is_employee = request.POST.get("is_employee") in ["on", "true", "1", True]
            volunteer.gender = request.POST.get("gender", volunteer.gender)
            volunteer.date_of_birth = request.POST.get("date_of_birth") or None
            volunteer.address = request.POST.get("address", volunteer.address)
            volunteer.city = request.POST.get("city", volunteer.city)
            volunteer.state = request.POST.get("state", volunteer.state)
            volunteer.pincode = request.POST.get("pincode", volunteer.pincode)
            volunteer.occupation = request.POST.get("occupation", volunteer.occupation)
            volunteer.qualification = request.POST.get("qualification", volunteer.qualification)
            volunteer.skills = request.POST.get("skills", volunteer.skills)
            volunteer.status = request.POST.get("status", volunteer.status)
            volunteer.remarks = request.POST.get("remarks", volunteer.remarks)
            volunteer.save()

            messages.success(request, f"Profile for {volunteer.first_name} {volunteer.last_name} updated successfully.")
            return redirect("volunteers:detail", pk=volunteer.pk)

    return render(
        request,
        "volunteers/volunteer_form.html",
        {
            "volunteer": volunteer,
            "errors": errors,
            "is_edit": True,
            "gender_choices": Volunteer.GENDER_CHOICES,
            "status_choices": Volunteer.STATUS_CHOICES,
            "departments": AEQUS_DEPARTMENTS,
            "plants": AEQUS_PLANTS,
            "academic_years": AEQUS_ACADEMIC_YEARS,
            "active_page": "volunteers",
        },
    )


def volunteer_delete(request, pk):
    volunteer = get_object_or_404(Volunteer, pk=pk)
    if request.method == "POST":
        name = str(volunteer)
        volunteer.delete()
        messages.success(request, f"Volunteer {name} was removed from the roster.")
        return redirect("volunteers:list")

    return redirect("volunteers:detail", pk=volunteer.pk)


def activity_create(request, pk):
    volunteer = get_object_or_404(Volunteer, pk=pk)

    if request.method == "POST":
        VolunteerActivity.objects.create(
            volunteer=volunteer,
            activity_name=request.POST.get("activity_name"),
            activity_date=request.POST.get("activity_date"),
            description=request.POST.get("description", ""),
            status=request.POST.get("status", "ASSIGNED"),
            remarks=request.POST.get("remarks", ""),
        )

        messages.success(request, "Activity recorded successfully.")
        return redirect("volunteers:detail", pk=volunteer.pk)

    return render(
        request,
        "volunteers/activity_form.html",
        {
            "volunteer": volunteer,
            "status_choices": VolunteerActivity.STATUS_CHOICES,
        },
    )


def event_participation_create(request, pk):
    volunteer = get_object_or_404(Volunteer, pk=pk)
    events = Event.objects.all()

    if request.method == "POST":
        event_id = request.POST.get("event")
        role = request.POST.get("role", "").strip()
        status = request.POST.get("participation_status", "ASSIGNED")
        hours = request.POST.get("hours_contributed", 0)
        remarks = request.POST.get("remarks", "").strip()

        if event_id:
            event = get_object_or_404(Event, pk=event_id)
            try:
                hours_val = float(hours) if hours else 0
            except ValueError:
                hours_val = 0

            EventParticipation.objects.update_or_create(
                volunteer=volunteer,
                event=event,
                defaults={
                    "role": role,
                    "participation_status": status,
                    "hours_contributed": hours_val,
                    "remarks": remarks,
                },
            )
            messages.success(request, f"Assigned to event '{event.title}'.")
        return redirect("volunteers:detail", pk=volunteer.pk)

    return render(
        request,
        "volunteers/event_participation_form.html",
        {
            "volunteer": volunteer,
            "events": events,
            "status_choices": EventParticipation.STATUS_CHOICES,
        },
    )


def volunteer_export_csv(request):
    volunteers = Volunteer.objects.annotate(
        total_hours=Sum("event_participations__hours_contributed"),
        event_count=Count("event_participations"),
    ).all()

    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if q:
        volunteers = volunteers.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q) |
            Q(skills__icontains=q)
        )
    if status_filter:
        volunteers = volunteers.filter(status=status_filter)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="aequs_volunteers.csv"'

    writer = csv.writer(response)
    writer.writerow(["ID", "First Name", "Last Name", "Employee Code", "Department", "Plant Location", "Email", "Phone", "Gender", "Status", "Occupation", "Skills", "Academic Year", "Events Attended", "Contributed Hours"])

    for v in volunteers:
        writer.writerow([
            v.id,
            v.first_name,
            v.last_name,
            v.employee_code or "—",
            v.department or "—",
            v.plant_location or "—",
            v.email,
            v.phone,
            v.get_gender_display(),
            v.get_status_display(),
            v.occupation or "—",
            v.skills or "—",
            v.academic_year or "—",
            v.event_count,
            round(v.total_hours or 0, 1),
        ])

    return response


def volunteer_export_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    volunteers = Volunteer.objects.annotate(
        total_hours=Sum("event_participations__hours_contributed"),
        event_count=Count("event_participations"),
    ).all()

    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if q:
        volunteers = volunteers.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q) |
            Q(employee_code__icontains=q) |
            Q(department__icontains=q) |
            Q(plant_location__icontains=q) |
            Q(skills__icontains=q)
        )
    if status_filter:
        volunteers = volunteers.filter(status=status_filter)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Volunteers Roster"

    title_font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    meta_font = Font(name="Calibri", size=10, italic=True, color="64748B")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="DD2D27", end_color="DD2D27", fill_type="solid")
    border_side = Side(border_style="thin", color="E2E8F0")
    cell_border = Border(top=border_side, bottom=border_side, left=border_side, right=border_side)

    ws.append(["Aequs Foundation - AEQATRA Volunteers Roster"])
    ws.cell(row=1, column=1).font = title_font
    ws.append([f"Total Enrolled: {len(volunteers)} volunteers | Status Filter: {status_filter or 'All'}"])
    ws.cell(row=2, column=1).font = meta_font
    ws.append([])

    headers = ["ID", "Name", "Employee Code", "Department", "Plant Location", "Email", "Phone", "Gender", "Status", "Occupation", "City", "Events", "Contributed Hours"]
    ws.append(headers)
    header_row_idx = ws.max_row
    for col_idx in range(1, len(headers) + 1):
        c = ws.cell(row=header_row_idx, column=col_idx)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center" if headers[col_idx-1] in ["ID", "Employee Code", "Gender", "Status", "Events", "Contributed Hours"] else "left")

    for v in volunteers:
        full_name = f"{v.first_name} {v.last_name}".strip()
        ws.append([
            v.id,
            full_name,
            v.employee_code or "—",
            v.department or "—",
            v.plant_location or "—",
            v.email,
            v.phone,
            v.get_gender_display(),
            v.get_status_display(),
            v.occupation or "—",
            v.city or "—",
            v.event_count,
            round(v.total_hours or 0, 1),
        ])
        curr_row = ws.max_row
        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(row=curr_row, column=col_idx)
            c.border = cell_border

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 35)

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    response = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="aequs_volunteers.xlsx"'
    return response


# =============================================================================
# UNIQUE VOLUNTEER FORM LINK GENERATION & SHARING
# =============================================================================

def generate_volunteer_form_link_json(request):
    """API endpoint to generate a fresh unique volunteer registration link asynchronously."""
    event_id = request.GET.get("event_id") or request.POST.get("event_id")
    role = request.GET.get("role") or request.POST.get("role") or "Volunteer"

    event = None
    if event_id:
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            event = None

    form_link = VolunteerFormLink.objects.create(event=event, role=role)
    form_url = request.build_absolute_uri(f"/volunteers/form/{form_link.token}/")
    qr_url = request.build_absolute_uri(f"/volunteers/form/qr/{form_link.token}/")
    return JsonResponse({
        "success": True,
        "token": form_link.token,
        "form_url": form_url,
        "qr_url": qr_url,
        "event_id": event.id if event else None,
        "event_title": event.title if event else None,
        "role": form_link.role,
    })


def create_volunteer_form_link(request):
    """Full-page form link generator analogous to events:create_form_link."""
    if request.method == "POST":
        event_id = request.POST.get("event_id")
        role = request.POST.get("role", "Volunteer").strip() or "Volunteer"
        event = None
        if event_id:
            try:
                event = Event.objects.get(pk=event_id)
            except Event.DoesNotExist:
                event = None
        form_link = VolunteerFormLink.objects.create(event=event, role=role)
        return redirect("volunteers:share_form", pk=form_link.pk)
    events = Event.objects.all().order_by("-event_date")
    return render(request, "volunteers/create_form_link.html", {"events": events})


def share_volunteer_form(request, pk):
    """Share page with unique URL and QR code analogous to events:share_form."""
    form_link = get_object_or_404(VolunteerFormLink, pk=pk, is_active=True)
    form_url = request.build_absolute_uri(f"/volunteers/form/{form_link.token}/")
    qr_url = request.build_absolute_uri(f"/volunteers/form/qr/{form_link.token}/")
    return render(
        request,
        "volunteers/share_form.html",
        {
            "form_link": form_link,
            "event": form_link.event,
            "form_url": form_url,
            "qr_url": qr_url,
        },
    )


def volunteer_form_qr(request, token=None, pk=None):
    """Generate and return live PNG QR code for volunteer registration form."""
    if token:
        form_link = get_object_or_404(VolunteerFormLink, token=token, is_active=True)
    elif pk:
        form_link = get_object_or_404(VolunteerFormLink, pk=pk, is_active=True)
    else:
        form_link = VolunteerFormLink.objects.filter(is_active=True).order_by("-created_at").first()
        if not form_link:
            form_link = VolunteerFormLink.objects.create()

    try:
        import qrcode
        import qrcode.constants
    except ImportError:
        return HttpResponse("QR code generation library is not installed.", status=501)

    form_url = request.build_absolute_uri(f"/volunteers/form/{form_link.token}/")
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=3,
    )
    qr.add_data(form_url)
    qr.make(fit=True)

    buffer = BytesIO()
    qr.make_image(fill_color="#1e293b", back_color="white").save(buffer, format="PNG")
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'inline; filename="volunteer-form-{form_link.token[:8]}.png"'
    return response


volunteer_form_qr_by_token = volunteer_form_qr
volunteer_registration_qr = volunteer_form_qr


# =============================================================================
# PUBLIC VOLUNTEER REGISTRATION FORM
# =============================================================================

def public_volunteer_registration(request, token=None):
    """Public standalone registration form for prospective community volunteers, secured with unique token."""
    form_link = None
    target_event = None
    if token:
        form_link = get_object_or_404(VolunteerFormLink, token=token, is_active=True)
        target_event = form_link.event
    if not target_event:
        event_id = request.GET.get("event_id") or request.POST.get("event_id")
        if event_id:
            try:
                target_event = Event.objects.get(pk=event_id)
            except (Event.DoesNotExist, ValueError):
                target_event = None

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        gender = request.POST.get("gender", "")
        date_of_birth = request.POST.get("date_of_birth") or None
        address = request.POST.get("address", "")
        city = request.POST.get("city", "")
        state = request.POST.get("state", "")
        pincode = request.POST.get("pincode", "")
        occupation = request.POST.get("occupation", "")
        qualification = request.POST.get("qualification", "")
        skills = request.POST.get("skills", "")
        remarks = request.POST.get("remarks", "")
        employee_code = request.POST.get("employee_code", "").strip()
        department = request.POST.get("department", "Aerospace Operations").strip()
        plant_location = request.POST.get("plant_location", "Belagavi SEZ").strip()
        academic_year = request.POST.get("academic_year", "2026-27").strip()
        is_employee = request.POST.get("is_employee") in ["on", "true", "1", True] or bool(employee_code)

        errors = []
        if not first_name:
            errors.append("First name is required.")
        if not email:
            errors.append("Email address is required.")
        if not phone:
            errors.append("Phone number is required.")

        volunteer = Volunteer.objects.filter(email__iexact=email).first()

        if errors:
            return render(
                request,
                "volunteers/public_volunteer_form.html",
                {
                    "errors": errors,
                    "form_data": request.POST,
                    "gender_choices": Volunteer.GENDER_CHOICES,
                    "departments": AEQUS_DEPARTMENTS,
                    "plants": AEQUS_PLANTS,
                    "academic_years": AEQUS_ACADEMIC_YEARS,
                    "form_link": form_link,
                    "event": target_event,
                },
            )

        if volunteer:
            volunteer.first_name = first_name
            if last_name:
                volunteer.last_name = last_name
            volunteer.phone = phone
            if employee_code:
                volunteer.employee_code = employee_code
                volunteer.is_employee = True
            if department:
                volunteer.department = department
            if plant_location:
                volunteer.plant_location = plant_location
            if academic_year:
                volunteer.academic_year = academic_year
            if gender:
                volunteer.gender = gender
            if date_of_birth:
                volunteer.date_of_birth = date_of_birth
            if address:
                volunteer.address = address
            if city:
                volunteer.city = city
            if state:
                volunteer.state = state
            if pincode:
                volunteer.pincode = pincode
            if occupation:
                volunteer.occupation = occupation
            if qualification:
                volunteer.qualification = qualification
            if skills:
                volunteer.skills = skills
            if remarks:
                volunteer.remarks = remarks
            volunteer.save()
        else:
            volunteer = Volunteer.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                employee_code=employee_code,
                department=department,
                plant_location=plant_location,
                academic_year=academic_year,
                is_employee=is_employee,
                gender=gender,
                date_of_birth=date_of_birth,
                address=address,
                city=city,
                state=state,
                pincode=pincode,
                occupation=occupation,
                qualification=qualification,
                skills=skills,
                status="ACTIVE",
                remarks=remarks,
            )

        # Specifically enroll in the event if this form was created for an event
        if target_event:
            role_to_assign = (form_link.role if form_link and form_link.role else None) or request.POST.get("role") or "Volunteer"
            EventParticipation.objects.update_or_create(
                volunteer=volunteer,
                event=target_event,
                defaults={
                    "role": role_to_assign,
                    "participation_status": "REQUESTED",
                    "remarks": f"Registered via event volunteer form link ({target_event.title})",
                }
            )

        try:
            from reports.models import log_activity, ActivityLog
            event_detail_str = f" for event '{target_event.title}'" if target_event else ""
            log_activity(
                request,
                action=f"Volunteer registration{event_detail_str}: {volunteer.first_name} {volunteer.last_name}",
                category="VOLUNTEER",
                action_type=ActivityLog.ActionType.CREATE,
                object_type="Volunteer",
                object_id=volunteer.pk,
                details=f"Volunteer registration: {volunteer.email} (token: {token or 'direct'}{event_detail_str})",
            )
        except Exception:
            pass

        base_url = reverse("volunteers:registration_success")
        if target_event:
            return redirect(f"{base_url}?event_id={target_event.pk}")
        return redirect(base_url)

    return render(
        request,
        "volunteers/public_volunteer_form.html",
        {
            "gender_choices": Volunteer.GENDER_CHOICES,
            "departments": AEQUS_DEPARTMENTS,
            "plants": AEQUS_PLANTS,
            "academic_years": AEQUS_ACADEMIC_YEARS,
            "form_link": form_link,
            "event": target_event,
        },
    )


def volunteer_registration_success(request):
    """Confirmation page displayed after a public volunteer registration."""
    event_id = request.GET.get("event_id")
    event = None
    if event_id:
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            event = None
    return render(request, "volunteers/registration_success.html", {"event": event})