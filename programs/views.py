from datetime import datetime, date
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

from .models import NGO, Project, Program, EVClassSession, Scholarship, CSRGrant, Location, MentorshipSession
from .forms import NGOForm, ProjectForm, ProgramForm, EVClassSessionForm, ScholarshipForm, LocationForm, MentorshipSessionForm
from schools.models import School, SchoolResource
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

    queryset = Project.objects.filter(is_archived=False).select_related("ngo").prefetch_related("target_schools", "programs", "locations")

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(lead_coordinator__icontains=search_query)
        )

    total_count = queryset.count()
    active_count = queryset.filter(status=Project.Status.ACTIVE).count()
    total_budget = queryset.aggregate(total=Sum("allocated_budget"))["total"] or 0
    spent_budget = queryset.aggregate(total=Sum("spent_budget"))["total"] or 0

    return render(
        request,
        "programs/project_list.html",
        {
            "projects": queryset,
            "total_count": total_count,
            "active_count": active_count,
            "total_budget": total_budget,
            "spent_budget": spent_budget,
            "status_choices": Project.Status.choices,
            "selected_status": status_filter,
            "search_query": search_query,
        },
    )


def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("ngo").prefetch_related("target_schools", "locations"),
        pk=pk,
    )
    programs = project.programs.filter(is_archived=False).prefetch_related("participating_schools", "locations")
    available_programs = Program.objects.filter(is_archived=False).exclude(project=project).order_by("title")
    csr_grants = project.csr_grants.all()
    scholarships = project.scholarships.filter(is_archived=False).select_related("student", "student__school")
    internships = project.internships.all().select_related("student", "school", "program")
    mentorship_sessions = project.mentorship_sessions.all().select_related("student")

    return render(
        request,
        "programs/project_detail.html",
        {
            "project": project,
            "programs": programs,
            "available_programs": available_programs,
            "csr_grants": csr_grants,
            "scholarships": scholarships,
            "internships": internships,
            "mentorship_sessions": mentorship_sessions,
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
            "title": "Create New Project",
        },
    )


def project_edit(request, pk):
    ensure_default_ngos()
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            messages.success(request, f"Project '{project.name}' ({project.code}) was updated successfully.")
            return redirect("programs:project_detail", pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    return render(
        request,
        "programs/project_form.html",
        {
            "form": form,
            "project": project,
            "is_edit": True,
            "title": f"Edit Project: {project.name}",
        },
    )


def project_link_program(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        program_id = request.POST.get("program_id")
        if program_id:
            program = get_object_or_404(Program, pk=program_id)
            program.project = project
            program.save(update_fields=["project"])
            messages.success(request, f"Program '{program.title}' is now linked to project '{project.name}'.")
        else:
            messages.error(request, "Please select a program to link.")
    return redirect("programs:project_detail", pk=project.pk)


def project_unlink_program(request, pk, program_id):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        program = get_object_or_404(Program, pk=program_id, project=project)
        program.project = None
        program.save(update_fields=["project"])
        messages.success(request, f"Program '{program.title}' unlinked from project '{project.name}'.")
    return redirect("programs:project_detail", pk=project.pk)


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
    project_filter = request.GET.get("project")
    taluk_filter = request.GET.get("taluk")
    search_query = request.GET.get("q", "").strip()

    queryset = Program.objects.filter(is_archived=False).select_related("project", "ngo").prefetch_related("participating_schools")

    if category_filter:
        queryset = queryset.filter(category=category_filter)
    if project_filter:
        if project_filter == "standalone":
            queryset = queryset.filter(project__isnull=True)
        else:
            queryset = queryset.filter(project_id=project_filter)
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
    projects = Project.objects.filter(is_archived=False).order_by("name")

    return render(
        request,
        "programs/program_list.html",
        {
            "programs": queryset,
            "total_count": queryset.count(),
            "category_choices": Program.Category.choices,
            "selected_category": category_filter,
            "projects": projects,
            "selected_project": project_filter,
            "taluks": sorted([t for t in taluks if t]),
            "selected_taluk": taluk_filter,
            "search_query": search_query,
        },
    )


def program_detail(request, pk):
    program = get_object_or_404(
        Program.objects.select_related("project", "ngo").prefetch_related("participating_schools", "locations"),
        pk=pk,
    )
    ev_sessions = program.ev_sessions.filter(is_archived=False)
    available_projects = Project.objects.filter(is_archived=False).order_by("name")
    scholarships = program.scholarships.filter(is_archived=False).select_related("student", "student__school")
    internships = program.internships.all().select_related("student", "school", "program")
    mentorship_sessions = program.mentorship_sessions.all().select_related("student")

    return render(
        request,
        "programs/program_detail.html",
        {
            "program": program,
            "ev_sessions": ev_sessions,
            "available_projects": available_projects,
            "scholarships": scholarships,
            "internships": internships,
            "mentorship_sessions": mentorship_sessions,
        },
    )



def program_create(request):
    ensure_default_ngos()
    preselected_project = None
    project_id = request.GET.get("project")

    initial_data = {}
    if project_id:
        preselected_project = Project.objects.filter(pk=project_id, is_archived=False).first()
        if preselected_project:
            initial_data["project"] = preselected_project.pk
            if preselected_project.ngo:
                initial_data["ngo"] = preselected_project.ngo.pk

    if request.method == "POST":
        form = ProgramForm(request.POST)
        if form.is_valid():
            program = form.save()
            messages.success(request, f"Program '{program.title}' at location '{program.location_name}' was registered successfully.")
            return redirect("programs:program_detail", pk=program.pk)
    else:
        form = ProgramForm(initial=initial_data)

    return render(
        request,
        "programs/program_form.html",
        {
            "form": form,
            "is_edit": False,
            "title": "Register Operational Program",
            "preselected_project": preselected_project,
        },
    )


def program_edit(request, pk):
    ensure_default_ngos()
    program = get_object_or_404(Program, pk=pk)
    if request.method == "POST":
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            program = form.save()
            messages.success(request, f"Program '{program.title}' was updated successfully.")
            return redirect("programs:program_detail", pk=program.pk)
    else:
        form = ProgramForm(instance=program)

    return render(
        request,
        "programs/program_form.html",
        {
            "form": form,
            "program": program,
            "is_edit": True,
            "title": f"Edit Program: {program.title}",
        },
    )


def program_link_project(request, pk):
    program = get_object_or_404(Program, pk=pk)
    if request.method == "POST":
        project_id = request.POST.get("project_id", "").strip()
        if project_id:
            project = get_object_or_404(Project, pk=project_id)
            program.project = project
            program.save(update_fields=["project"])
            messages.success(request, f"Program '{program.title}' is now linked to parent project '{project.name}'.")
        else:
            program.project = None
            program.save(update_fields=["project"])
            messages.success(request, f"Program '{program.title}' is now standalone (unlinked).")
    return redirect("programs:program_detail", pk=program.pk)


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
    schools = ngo.partner_schools.all().order_by("name")
    total_students = sum(s.student_strength for s in schools)
    programs = ngo.programs.filter(is_archived=False)
    ev_sessions = ngo.ev_sessions.filter(is_archived=False)[:10]
    allocated_resources = SchoolResource.objects.filter(school__in=schools).select_related("school").order_by("-updated_at")

    return render(
        request,
        "programs/ngo_detail.html",
        {
            "ngo": ngo,
            "schools": schools,
            "total_students": total_students,
            "programs": programs,
            "ev_sessions": ev_sessions,
            "allocated_resources": allocated_resources,
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
            "title": "Register NGO Partner",
        },
    )


def ngo_edit(request, pk):
    ngo = get_object_or_404(NGO, pk=pk)
    if request.method == "POST":
        form = NGOForm(request.POST, instance=ngo)
        if form.is_valid():
            ngo = form.save()
            messages.success(request, f"NGO partner dossier for '{ngo.name}' updated successfully.")
            return redirect("programs:ngo_detail", pk=ngo.pk)
    else:
        form = NGOForm(instance=ngo)

    return render(
        request,
        "programs/ngo_form.html",
        {
            "form": form,
            "is_edit": True,
            "ngo": ngo,
            "title": f"Edit Dossier: {ngo.name}",
        },
    )


def ngo_allocate_resource(request, pk):
    ngo = get_object_or_404(NGO, pk=pk)
    if request.method == "POST":
        school_id = request.POST.get("school_id")
        resource_name = request.POST.get("resource_name", "").strip()
        quantity_raw = request.POST.get("quantity", "1")
        status = request.POST.get("status", "Active").strip() or "Active"
        details = request.POST.get("details", "").strip()

        school = get_object_or_404(School, pk=school_id)
        try:
            quantity = max(1, int(quantity_raw))
        except (ValueError, TypeError):
            quantity = 1

        if not resource_name:
            messages.error(request, "Resource Name is required for allocation.")
            return redirect("programs:ngo_detail", pk=ngo.pk)

        note = f"Allocated via NGO partner '{ngo.name}'"
        full_details = f"{details} (Partner: {ngo.name})".strip() if details else note
        SchoolResource.objects.create(
            school=school,
            resource_name=resource_name,
            status=status,
            quantity=quantity,
            last_updated_note=note,
            details=full_details,
        )

        try:
            from distributions.models import BenefitType, RecipientType
            Distribution.objects.create(
                school=school,
                recipient_type=RecipientType.SCHOOL,
                benefit_type=BenefitType.SCHOOL_ESSENTIAL,
                quantity=quantity,
                remarks=f"NGO Allocation ({ngo.name}): {resource_name}. {details}".strip(),
            )
        except Exception:
            pass

        messages.success(
            request,
            f"Successfully allocated {quantity}x '{resource_name}' to {school.name}. Reflected in student profiles.",
        )
    return redirect("programs:ngo_detail", pk=ngo.pk)


# ============================================================================
# 5. SCHOLARSHIP TRACKING VIEWS (Module 8 & Module 9)
# ============================================================================

def scholarship_list(request):
    category_tab = request.GET.get("category", "all")
    status_filter = request.GET.get("status")
    search_query = request.GET.get("q", "").strip()

    queryset = Scholarship.objects.filter(is_archived=False).select_related("student", "student__school", "project", "program")

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
            Q(employee_code__icontains=search_query) |
            Q(project__name__icontains=search_query) |
            Q(program__title__icontains=search_query)
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
    initial = {"category": category}
    if request.GET.get("project"):
        initial["project"] = request.GET.get("project")
    if request.GET.get("program"):
        initial["program"] = request.GET.get("program")

    if request.method == "POST":
        form = ScholarshipForm(request.POST)
        if form.is_valid():
            scholarship = form.save()
            messages.success(request, f"Scholarship record for '{scholarship.student.student_name}' ({scholarship.scheme_name}) recorded successfully.")
            return redirect("programs:scholarship_list")
    else:
        form = ScholarshipForm(initial=initial)

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


# ============================================================================
# 8. LOCATION MASTER VIEWS (Module 16)
# ============================================================================

def location_list(request):
    search_query = request.GET.get("q", "").strip()
    district_filter = request.GET.get("district", "").strip()

    queryset = Location.objects.all()
    if district_filter:
        queryset = queryset.filter(district=district_filter)
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(taluk__icontains=search_query) |
            Q(village_or_town__icontains=search_query)
        )

    districts = Location.objects.values_list("district", flat=True).distinct()

    return render(
        request,
        "programs/location_list.html",
        {
            "locations": queryset,
            "total_count": queryset.count(),
            "active_count": queryset.filter(is_active=True).count(),
            "districts": sorted([d for d in districts if d]),
            "selected_district": district_filter,
            "search_query": search_query,
        },
    )


def location_create(request):
    if request.method == "POST":
        form = LocationForm(request.POST)
        if form.is_valid():
            loc = form.save()
            messages.success(request, f"Location '{loc.name}' ({loc.code}) created successfully.")
            return redirect("programs:location_list")
    else:
        form = LocationForm()

    return render(
        request,
        "programs/location_form.html",
        {
            "form": form,
            "is_edit": False,
            "title": "Add New Location",
        },
    )


def location_edit(request, pk):
    loc = get_object_or_404(Location, pk=pk)
    if request.method == "POST":
        form = LocationForm(request.POST, instance=loc)
        if form.is_valid():
            loc = form.save()
            messages.success(request, f"Location '{loc.name}' ({loc.code}) updated successfully.")
            return redirect("programs:location_list")
    else:
        form = LocationForm(instance=loc)

    return render(
        request,
        "programs/location_form.html",
        {
            "form": form,
            "location": loc,
            "is_edit": True,
            "title": f"Edit Location: {loc.name}",
        },
    )


def location_delete(request, pk):
    loc = get_object_or_404(Location, pk=pk)
    if request.method == "POST":
        name = loc.name
        loc.delete()
        messages.success(request, f"Location '{name}' was deleted.")
    return redirect("programs:location_list")


# ============================================================================
# 9. MENTORSHIP SESSION VIEWS
# ============================================================================

def mentorship_list(request):
    status_filter = request.GET.get("status", "").strip()
    search_query = request.GET.get("q", "").strip()
    project_filter = request.GET.get("project", "").strip()
    program_filter = request.GET.get("program", "").strip()

    queryset = MentorshipSession.objects.select_related("project", "program", "student", "student__school").all()

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if project_filter:
        queryset = queryset.filter(project_id=project_filter)
    if program_filter:
        queryset = queryset.filter(program_id=program_filter)
    if search_query:
        queryset = queryset.filter(
            Q(session_title__icontains=search_query) |
            Q(session_code__icontains=search_query) |
            Q(mentor_name__icontains=search_query) |
            Q(student__student_name__icontains=search_query) |
            Q(topic__icontains=search_query)
        )

    projects = Project.objects.filter(is_archived=False).order_by("name")
    programs = Program.objects.filter(is_archived=False).order_by("title")

    return render(
        request,
        "programs/mentorship_list.html",
        {
            "sessions": queryset,
            "total_count": queryset.count(),
            "scheduled_count": queryset.filter(status=MentorshipSession.Status.SCHEDULED).count(),
            "completed_count": queryset.filter(status=MentorshipSession.Status.COMPLETED).count(),
            "status_choices": MentorshipSession.Status.choices,
            "selected_status": status_filter,
            "projects": projects,
            "selected_project": project_filter,
            "programs": programs,
            "selected_program": program_filter,
            "search_query": search_query,
        },
    )


def mentorship_create(request):
    initial = {}
    if request.GET.get("project"):
        initial["project"] = request.GET.get("project")
    if request.GET.get("program"):
        initial["program"] = request.GET.get("program")
    if request.GET.get("student"):
        initial["student"] = request.GET.get("student")

    if request.method == "POST":
        form = MentorshipSessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            messages.success(request, f"Mentorship session '{session.session_title}' ({session.session_code}) created successfully.")
            return redirect("programs:mentorship_list")
    else:
        form = MentorshipSessionForm(initial=initial)

    return render(
        request,
        "programs/mentorship_form.html",
        {
            "form": form,
            "is_edit": False,
            "title": "Log Mentorship Session",
        },
    )


def mentorship_edit(request, pk):
    session = get_object_or_404(MentorshipSession, pk=pk)
    if request.method == "POST":
        form = MentorshipSessionForm(request.POST, instance=session)
        if form.is_valid():
            session = form.save()
            messages.success(request, f"Mentorship session '{session.session_title}' ({session.session_code}) updated.")
            return redirect("programs:mentorship_list")
    else:
        form = MentorshipSessionForm(instance=session)

    return render(
        request,
        "programs/mentorship_form.html",
        {
            "form": form,
            "session": session,
            "is_edit": True,
            "title": f"Edit Mentorship Session: {session.session_code}",
        },
    )


def mentorship_delete(request, pk):
    session = get_object_or_404(MentorshipSession, pk=pk)
    if request.method == "POST":
        code = session.session_code
        session.delete()
        messages.success(request, f"Mentorship session '{code}' deleted.")
    return redirect("programs:mentorship_list")

