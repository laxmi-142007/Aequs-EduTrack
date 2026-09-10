from datetime import datetime, date
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

from .models import NGO, Project, Program, EVClassSession, Scholarship, CSRGrant
from .forms import NGOForm, ProjectForm, ProgramForm, EVClassSessionForm, ScholarshipForm
from schools.models import School
from students.models import Student
from distributions.models import Distribution


# ============================================================================
# HELPER: ENSURE DEFAULT NGOS (Pratham, Agastya, Youth for Seva)
# ============================================================================

def ensure_default_ngos():
    """
    Auto-seeds the 3 core NGO partners requested by Aequs Foundation
    if they do not already exist.
    """
    defaults = [
        {
            "name": "Pratham",
            "code": "PRATHAM",
            "focus_areas": "Foundational Literacy & Numeracy (FLN), Read India Drives",
            "contact_person": "State Lead Coordinator",
            "phone": "+91 80 2345 6789",
            "email": "karnataka@pratham.org",
            "headquarters": "Karnataka Hub",
        },
        {
            "name": "Agastya International Foundation",
            "code": "AGASTYA",
            "focus_areas": "Mobile Science Labs, Hands-on STEM Discovery, Science Fairs",
            "contact_person": "Regional Operations Head",
            "phone": "+91 831 245 8899",
            "email": "belagavi@agastya.org",
            "headquarters": "Belagavi Science Center",
        },
        {
            "name": "Youth for Seva",
            "code": "YFS",
            "focus_areas": "Corporate Volunteer Tutoring, Mentorship Drives, Chiguru Festival",
            "contact_person": "Volunteer Lead",
            "phone": "+91 831 249 1122",
            "email": "belagavi@youthforseva.org",
            "headquarters": "Belagavi Chapter",
        },
    ]
    for item in defaults:
        NGO.objects.get_or_create(code=item["code"], defaults=item)


# ============================================================================
# 1. PROJECT MANAGEMENT VIEWS (Module 7)
# ============================================================================

def project_list(request):
    ensure_default_ngos()
    status_filter = request.GET.get("status")
    search_query = request.GET.get("q", "").strip()

    queryset = Project.objects.filter(is_archived=False).select_related("ngo").prefetch_related("target_schools")

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if search_query:
        queryset = queryset.filter(Q(name__icontains=search_query) | Q(code__icontains=search_query))

    total_count = Project.objects.filter(is_archived=False).count()
    active_count = Project.objects.filter(is_archived=False, status=Project.Status.ACTIVE).count()
    total_budget = Project.objects.filter(is_archived=False).aggregate(Sum("allocated_budget"))["allocated_budget__sum"] or 0
    spent_budget = Project.objects.filter(is_archived=False).aggregate(Sum("spent_budget"))["spent_budget__sum"] or 0

    return render(
        request,
        "programs/project_list.html",
        {
            "projects": queryset,
            "total_count": total_count,
            "active_count": active_count,
            "total_budget": total_budget,
            "spent_budget": spent_budget,
            "selected_status": status_filter,
            "search_query": search_query,
            "status_choices": Project.Status.choices,
        },
    )


def project_detail(request, pk):
    project = get_object_or_404(Project.objects.select_related("ngo").prefetch_related("target_schools"), pk=pk)
    programs = project.programs.filter(is_archived=False)
    csr_grants = project.csr_grants.all()

    return render(
        request,
        "programs/project_detail.html",
        {
            "project": project,
            "programs": programs,
            "csr_grants": csr_grants,
        },
    )


def project_create(request):
    ensure_default_ngos()
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, f"Project '{project.name}' ({project.code}) was created successfully.")
            return redirect("programs:project_detail", pk=project.pk)
    else:
        form = ProjectForm()

    return render(
        request,
        "programs/project_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


def project_toggle_archive(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.is_archived = not project.is_archived
    if project.is_archived:
        project.status = Project.Status.ARCHIVED
    else:
        project.status = Project.Status.ACTIVE
    project.save()

    state = "archived" if project.is_archived else "restored"
    messages.success(request, f"Project '{project.name}' has been {state}.")
    return redirect("programs:project_list" if not project.is_archived else "programs:archive_portal")


# ============================================================================
# 2. PROGRAM MANAGEMENT VIEWS WITH MANDATORY LOCATION (Module 11 & 16)
# ============================================================================

def program_list(request):
    ensure_default_ngos()
    category_filter = request.GET.get("category")
    taluk_filter = request.GET.get("taluk")
    search_query = request.GET.get("q", "").strip()

    queryset = Program.objects.filter(is_archived=False).select_related("project", "ngo").prefetch_related("participating_schools")

    if category_filter:
        queryset = queryset.filter(category=category_filter)
    if taluk_filter:
        queryset = queryset.filter(taluk__iexact=taluk_filter)
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(location_name__icontains=search_query) |
            Q(village_or_town__icontains=search_query)
        )

    taluks = Program.objects.filter(is_archived=False).values_list("taluk", flat=True).distinct()

    return render(
        request,
        "programs/program_list.html",
        {
            "programs": queryset,
            "total_count": queryset.count(),
            "category_choices": Program.Category.choices,
            "selected_category": category_filter,
            "taluks": sorted([t for t in taluks if t]),
            "selected_taluk": taluk_filter,
            "search_query": search_query,
        },
    )


def program_detail(request, pk):
    program = get_object_or_404(Program.objects.select_related("project", "ngo").prefetch_related("participating_schools"), pk=pk)
    ev_sessions = program.ev_sessions.filter(is_archived=False)

    return render(
        request,
        "programs/program_detail.html",
        {
            "program": program,
            "ev_sessions": ev_sessions,
        },
    )


def program_create(request):
    ensure_default_ngos()
    if request.method == "POST":
        form = ProgramForm(request.POST)
        if form.is_valid():
            program = form.save()
            messages.success(request, f"Program '{program.title}' at location '{program.location_name}' was registered successfully.")
            return redirect("programs:program_detail", pk=program.pk)
    else:
        form = ProgramForm()

    return render(
        request,
        "programs/program_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


def program_toggle_archive(request, pk):
    program = get_object_or_404(Program, pk=pk)
    program.is_archived = not program.is_archived
    if program.is_archived:
        program.status = Program.Status.COMPLETED
    else:
        program.status = Program.Status.ACTIVE
    program.save()

    state = "archived" if program.is_archived else "restored"
    messages.success(request, f"Program '{program.title}' has been {state}.")
    return redirect("programs:program_list" if not program.is_archived else "programs:archive_portal")


# ============================================================================
# 3. DETAILED EV CLASS TRACKING VIEWS (Module 4)
# ============================================================================

def ev_class_list(request):
    ensure_default_ngos()
    school_id = request.GET.get("school")
    search_query = request.GET.get("q", "").strip()

    queryset = EVClassSession.objects.filter(is_archived=False).select_related("school", "ngo", "program")

    if school_id:
        queryset = queryset.filter(school_id=school_id)
    if search_query:
        queryset = queryset.filter(
            Q(session_title__icontains=search_query) |
            Q(topic__icontains=search_query) |
            Q(facilitator_name__icontains=search_query) |
            Q(session_code__icontains=search_query)
        )

    schools = School.objects.all().order_by("name")
    total_sessions = queryset.count()
    completed_sessions = queryset.filter(status=EVClassSession.Status.COMPLETED).count()
    total_attendees = queryset.aggregate(Sum("attendee_count"))["attendee_count__sum"] or 0

    return render(
        request,
        "programs/ev_class_list.html",
        {
            "sessions": queryset,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "total_attendees": total_attendees,
            "schools": schools,
            "selected_school": school_id,
            "search_query": search_query,
        },
    )


def ev_class_detail(request, pk):
    session = get_object_or_404(EVClassSession.objects.select_related("school", "ngo", "program").prefetch_related("students"), pk=pk)
    return render(
        request,
        "programs/ev_class_detail.html",
        {
            "session": session,
            "students": session.students.all(),
        },
    )


def ev_class_create(request):
    ensure_default_ngos()
    if request.method == "POST":
        form = EVClassSessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            messages.success(request, f"EV Class Session '{session.session_title}' ({session.session_code}) logged successfully.")
            return redirect("programs:ev_class_detail", pk=session.pk)
    else:
        form = EVClassSessionForm()

    return render(
        request,
        "programs/ev_class_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


def ev_class_toggle_archive(request, pk):
    session = get_object_or_404(EVClassSession, pk=pk)
    session.is_archived = not session.is_archived
    session.save()
    state = "archived" if session.is_archived else "restored"
    messages.success(request, f"EV Class Session '{session.session_code}' has been {state}.")
    return redirect("programs:ev_class_list" if not session.is_archived else "programs:archive_portal")


# ============================================================================
# 4. NGO MANAGEMENT VIEWS (Module 5: Pratham, Agastya, Youth for Seva)
# ============================================================================

def ngo_list(request):
    ensure_default_ngos()
    ngos = NGO.objects.filter(is_active=True).prefetch_related("partner_schools", "programs", "ev_sessions")

    return render(
        request,
        "programs/ngo_list.html",
        {
            "ngos": ngos,
            "total_count": ngos.count(),
        },
    )


def ngo_detail(request, pk):
    ngo = get_object_or_404(NGO.objects.prefetch_related("partner_schools", "programs", "ev_sessions"), pk=pk)
    programs = ngo.programs.filter(is_archived=False)
    ev_sessions = ngo.ev_sessions.filter(is_archived=False)[:10]

    return render(
        request,
        "programs/ngo_detail.html",
        {
            "ngo": ngo,
            "programs": programs,
            "ev_sessions": ev_sessions,
        },
    )


def ngo_create(request):
    if request.method == "POST":
        form = NGOForm(request.POST)
        if form.is_valid():
            ngo = form.save()
            messages.success(request, f"NGO partner '{ngo.name}' added successfully.")
            return redirect("programs:ngo_detail", pk=ngo.pk)
    else:
        form = NGOForm()

    return render(
        request,
        "programs/ngo_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


# ============================================================================
# 5. SCHOLARSHIP TRACKING VIEWS (Module 8 & Module 9)
# ============================================================================

def scholarship_list(request):
    category_tab = request.GET.get("category", "all")
    status_filter = request.GET.get("status")
    search_query = request.GET.get("q", "").strip()

    queryset = Scholarship.objects.filter(is_archived=False).select_related("student", "student__school")

    if category_tab == "government":
        queryset = queryset.filter(category=Scholarship.Category.GOVERNMENT)
    elif category_tab == "employee_special":
        queryset = queryset.filter(category=Scholarship.Category.EMPLOYEE_SPECIAL)
    elif category_tab == "foundation":
        queryset = queryset.filter(category=Scholarship.Category.FOUNDATION)

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if search_query:
        queryset = queryset.filter(
            Q(student__student_name__icontains=search_query) |
            Q(application_number__icontains=search_query) |
            Q(scheme_name__icontains=search_query) |
            Q(employee_name__icontains=search_query) |
            Q(employee_code__icontains=search_query)
        )

    # Aggregates
    total_sanctioned = queryset.aggregate(Sum("sanctioned_amount"))["sanctioned_amount__sum"] or 0
    total_disbursed = queryset.aggregate(Sum("disbursed_amount"))["disbursed_amount__sum"] or 0
    gov_count = Scholarship.objects.filter(is_archived=False, category=Scholarship.Category.GOVERNMENT).count()
    emp_count = Scholarship.objects.filter(is_archived=False, category=Scholarship.Category.EMPLOYEE_SPECIAL).count()
    fnd_count = Scholarship.objects.filter(is_archived=False, category=Scholarship.Category.FOUNDATION).count()

    return render(
        request,
        "programs/scholarship_list.html",
        {
            "scholarships": queryset,
            "active_tab": category_tab,
            "total_count": queryset.count(),
            "total_sanctioned": total_sanctioned,
            "total_disbursed": total_disbursed,
            "gov_count": gov_count,
            "emp_count": emp_count,
            "fnd_count": fnd_count,
            "status_choices": Scholarship.Status.choices,
            "selected_status": status_filter,
            "search_query": search_query,
        },
    )


def scholarship_create(request):
    category = request.GET.get("category", Scholarship.Category.FOUNDATION)
    if request.method == "POST":
        form = ScholarshipForm(request.POST)
        if form.is_valid():
            scholarship = form.save()
            messages.success(request, f"Scholarship record for '{scholarship.student.student_name}' ({scholarship.scheme_name}) recorded successfully.")
            return redirect("programs:scholarship_list")
    else:
        form = ScholarshipForm(initial={"category": category})

    return render(
        request,
        "programs/scholarship_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


def scholarship_update_status(request, pk):
    scholarship = get_object_or_404(Scholarship, pk=pk)
    new_status = request.POST.get("status")
    if new_status in dict(Scholarship.Status.choices):
        scholarship.status = new_status
        if new_status == Scholarship.Status.DISBURSED and not scholarship.disbursement_date:
            scholarship.disbursement_date = timezone.localdate()
            if scholarship.disbursed_amount == 0 and scholarship.sanctioned_amount > 0:
                scholarship.disbursed_amount = scholarship.sanctioned_amount
        scholarship.save()
        messages.success(request, f"Status updated to '{scholarship.get_status_display()}'.")
    return redirect("programs:scholarship_list")


def scholarship_toggle_archive(request, pk):
    scholarship = get_object_or_404(Scholarship, pk=pk)
    scholarship.is_archived = not scholarship.is_archived
    scholarship.save()
    state = "archived" if scholarship.is_archived else "restored"
    messages.success(request, f"Scholarship record has been {state}.")
    return redirect("programs:scholarship_list" if not scholarship.is_archived else "programs:archive_portal")


# ============================================================================
# 6. MONTHLY TRACKING VIEW (Module 6)
# ============================================================================

def monthly_tracking(request):
    ensure_default_ngos()
    today = timezone.localdate()
    selected_year = int(request.GET.get("year", today.year))
    selected_month = int(request.GET.get("month", today.month))

    # Metrics for selected month
    ev_sessions = EVClassSession.objects.filter(
        session_date__year=selected_year,
        session_date__month=selected_month,
        is_archived=False,
    )
    ev_students_reached = ev_sessions.aggregate(Sum("attendee_count"))["attendee_count__sum"] or 0

    distributions = Distribution.objects.filter(
        distribution_date__year=selected_year,
        distribution_date__month=selected_month,
    )
    units_distributed = distributions.aggregate(Sum("quantity"))["quantity__sum"] or 0

    scholarships = Scholarship.objects.filter(
        disbursement_date__year=selected_year,
        disbursement_date__month=selected_month,
        is_archived=False,
    )
    scholarship_disbursed_total = scholarships.aggregate(Sum("disbursed_amount"))["disbursed_amount__sum"] or 0

    # NGO activity count in this month
    ngos_active = NGO.objects.filter(
        ev_sessions__session_date__year=selected_year,
        ev_sessions__session_date__month=selected_month,
    ).distinct()

    # Month list for dropdown
    month_names = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December"),
    ]
    years = list(range(today.year - 2, today.year + 2))

    return render(
        request,
        "programs/monthly_tracking.html",
        {
            "selected_year": selected_year,
            "selected_month": selected_month,
            "selected_month_name": dict(month_names).get(selected_month, ""),
            "month_names": month_names,
            "years": years,
            "ev_sessions": ev_sessions,
            "ev_sessions_count": ev_sessions.count(),
            "ev_students_reached": ev_students_reached,
            "distributions": distributions[:15],
            "units_distributed": units_distributed,
            "scholarships": scholarships,
            "scholarship_disbursed_total": scholarship_disbursed_total,
            "ngos_active": ngos_active,
        },
    )


# ============================================================================
# 7. ARCHIVE PORTAL (Module 17)
# ============================================================================

def archive_portal(request):
    tab = request.GET.get("tab", "projects")

    archived_projects = Project.objects.filter(is_archived=True)
    archived_programs = Program.objects.filter(is_archived=True)
    archived_ev = EVClassSession.objects.filter(is_archived=True)
    archived_scholarships = Scholarship.objects.filter(is_archived=True)
    inactive_students = Student.objects.filter(status=Student.Status.INACTIVE)

    return render(
        request,
        "programs/archive_portal.html",
        {
            "active_tab": tab,
            "archived_projects": archived_projects,
            "archived_programs": archived_programs,
            "archived_ev": archived_ev,
            "archived_scholarships": archived_scholarships,
            "inactive_students": inactive_students,
            "projects_count": archived_projects.count(),
            "programs_count": archived_programs.count(),
            "ev_count": archived_ev.count(),
            "scholarships_count": archived_scholarships.count(),
            "students_count": inactive_students.count(),
        },
    )


def archive_restore(request, model_type, pk):
    if model_type == "project":
        obj = get_object_or_404(Project, pk=pk)
        obj.is_archived = False
        obj.status = Project.Status.ACTIVE
        obj.save()
        messages.success(request, f"Project '{obj.name}' restored to active state.")
    elif model_type == "program":
        obj = get_object_or_404(Program, pk=pk)
        obj.is_archived = False
        obj.status = Program.Status.ACTIVE
        obj.save()
        messages.success(request, f"Program '{obj.title}' restored to active state.")
    elif model_type == "ev":
        obj = get_object_or_404(EVClassSession, pk=pk)
        obj.is_archived = False
        obj.save()
        messages.success(request, f"EV Session '{obj.session_code}' restored.")
    elif model_type == "scholarship":
        obj = get_object_or_404(Scholarship, pk=pk)
        obj.is_archived = False
        obj.save()
        messages.success(request, f"Scholarship record restored.")
    elif model_type == "student":
        obj = get_object_or_404(Student, pk=pk)
        obj.status = Student.Status.ACTIVE
        obj.save()
        messages.success(request, f"Student '{obj.student_name}' restored to Active status.")

    return redirect("programs:archive_portal")
