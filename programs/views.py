import os
import csv
import io
from datetime import datetime, date
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import transaction

from .models import NGO, Project, Program, EVClassSession, Scholarship, CSRGrant, Location, MentorshipSession, IndustryVisit, MikePropenScholarshipApplication
from .forms import NGOForm, ProjectForm, ProgramForm, EVClassSessionForm, ScholarshipForm, LocationForm, MentorshipSessionForm, IndustryVisitForm
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


def resolve_tracker_programme(program):
    """
    Maps a Program to its corresponding WeeklyTrackerSession Programme choice.
    """
    if not program:
        return None
    t = f"{program.code or ''} {program.title or ''}".upper()
    if "NMMS" in t:
        return "NMMS"
    if "STEP" in t or "SEP" in t or "STUDENT EXCEL" in t:
        return "SEP"
    if "IGNITE" in t and ("HUBBALLI" in t or "HBL" in t):
        return "IGNITE_HBL"
    if "IGNITE" in t:
        return "IGNITE_BGM"
    if "MSL" in t or "MOBILE SCIENCE" in t:
        return "MSL"
    if "AVISHKAR" in t:
        return "AVISHKAR"
    if "VASANTHA" in t:
        return "VASANTHA"
    if "YUVACHARYA" in t:
        return "YUVACHARYA"
    if "HEALTH" in t or "HHP" in t or "CHAAP" in t:
        return "CHAAP_JR"
    if "AHAP" in t:
        return "CHAAP_YUVA"
    if "NOTEBOOK" in t or "OPN" in t:
        return "OPN"
    if "CAMP" in t:
        return "CAMP"
    if "READING" in t:
        return "READING"
    return None


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

    from trackers.models import WeeklyTrackerSession
    project_program_keys = set()
    for prg in programs:
        k = resolve_tracker_programme(prg)
        if k:
            project_program_keys.add(k)

    project_sessions = []
    if project_program_keys:
        ws_qs = WeeklyTrackerSession.objects.filter(programme__in=project_program_keys).select_related("school", "ngo").order_by("-session_date", "-id")[:60]
        for ws in ws_qs:
            project_sessions.append({
                "date": ws.session_date,
                "date_display": ws.session_date.strftime("%d %b %Y") if ws.session_date else f"{ws.month_name} {ws.day_number or ''}".strip(),
                "programme": ws.get_programme_display(),
                "school_name": ws.school.name if ws.school else (ws.raw_location_or_activity or "—"),
                "standard": ws.standard or "All",
                "topic": ws.topic or ws.raw_location_or_activity or "Module Session",
                "instructor": ws.instructor_name or "Faculty Facilitator",
                "session_type": ws.session_type or "Practical",
                "boys": ws.boys_present,
                "girls": ws.girls_present,
                "exposures": ws.total_exposures,
                "teacher_present": ws.teacher_present,
            })
    project_sessions_count = len(project_sessions)
    project_exposures_sum = sum(s["exposures"] for s in project_sessions)

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
            "project_sessions": project_sessions,
            "project_sessions_count": project_sessions_count,
            "project_exposures_sum": project_exposures_sum,
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
    project_filter = request.GET.get("project")
    taluk_filter = request.GET.get("taluk")
    search_query = request.GET.get("q", "").strip()

    queryset = Program.objects.filter(is_archived=False).select_related("project", "ngo").prefetch_related("participating_schools")

    if project_filter:
        if project_filter == "standalone":
            queryset = queryset.filter(project__isnull=True)
        else:
            queryset = queryset.filter(project_id=project_filter)
    if taluk_filter:
        queryset = queryset.filter(taluk__iexact=taluk_filter)
    if search_query:
        norm_q = search_query.replace("tt", "t").replace("ii", "i")
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(title__icontains=norm_q) |
            Q(code__icontains=search_query) |
            Q(location_name__icontains=search_query) |
            Q(location_name__icontains=norm_q) |
            Q(description__icontains=search_query) |
            Q(description__icontains=norm_q) |
            Q(village_or_town__icontains=search_query) |
            Q(taluk__icontains=search_query) |
            Q(district__icontains=search_query)
        )

    taluks = Program.objects.filter(is_archived=False).values_list("taluk", flat=True).distinct()
    projects = Project.objects.filter(is_archived=False).order_by("name")

    return render(
        request,
        "programs/program_list.html",
        {
            "programs": queryset,
            "total_count": queryset.count(),
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
    ev_sessions = program.ev_sessions.filter(is_archived=False).select_related("school")
    available_projects = Project.objects.filter(is_archived=False).order_by("name")
    scholarships = program.scholarships.filter(is_archived=False).select_related("student", "student__school")
    internships = program.internships.all().select_related("student", "school", "program")
    mentorship_sessions = program.mentorship_sessions.all().select_related("student")

    from .roster import get_program_school_roster
    roster_data = get_program_school_roster(program)

    from trackers.models import WeeklyTrackerSession
    prog_key = resolve_tracker_programme(program)

    weekly_sessions_qs = WeeklyTrackerSession.objects.none()
    if prog_key:
        weekly_sessions_qs = WeeklyTrackerSession.objects.filter(programme=prog_key).select_related("school", "ngo")
    elif program.participating_schools.exists():
        weekly_sessions_qs = WeeklyTrackerSession.objects.filter(school__in=program.participating_schools.all()).select_related("school", "ngo")
    elif program.ngo:
        weekly_sessions_qs = WeeklyTrackerSession.objects.filter(ngo=program.ngo).select_related("school", "ngo")

    combined_sessions = []
    # Add WeeklyTrackerSessions
    for ws in weekly_sessions_qs.order_by("-session_date", "-id")[:250]:
        combined_sessions.append({
            "source": "weekly_tracker",
            "date": ws.session_date,
            "date_display": ws.session_date.strftime("%d %b %Y") if ws.session_date else f"{ws.month_name} {ws.day_number or ''}".strip(),
            "code": f"SES-{ws.id:04d}",
            "title": ws.topic or ws.raw_location_or_activity or "Field Session",
            "school_name": ws.school.name if ws.school else (ws.raw_location_or_activity or "—"),
            "school_id": ws.school_id,
            "standard": ws.standard or "All",
            "division": ws.division or "",
            "timing": ws.timing or "—",
            "topic": ws.topic or ws.raw_location_or_activity or "Curriculum Session",
            "instructor": ws.instructor_name or "Faculty Facilitator",
            "session_type": ws.session_type or "Practical",
            "boys": ws.boys_present,
            "girls": ws.girls_present,
            "total_exposures": ws.total_exposures,
            "teacher_present": ws.teacher_present,
            "status": "COMPLETED",
        })

    # Add EVClassSessions
    for ev in ev_sessions.order_by("-session_date", "-id"):
        combined_sessions.append({
            "source": "ev_class",
            "date": ev.session_date,
            "date_display": ev.session_date.strftime("%d %b %Y") if ev.session_date else "—",
            "code": ev.session_code,
            "title": ev.session_title,
            "school_name": ev.school.school_name if ev.school else "—",
            "school_id": ev.school_id,
            "standard": f"Grade {ev.grade_level}" if ev.grade_level else "All",
            "division": "",
            "timing": f"{ev.duration_minutes} min" if ev.duration_minutes else "—",
            "topic": ev.topic or "Science Workshop",
            "instructor": ev.facilitator_name or "Facilitator",
            "session_type": "EV Session",
            "boys": int(ev.attendee_count / 2) if ev.attendee_count else 0,
            "girls": int(ev.attendee_count / 2) if ev.attendee_count else 0,
            "total_exposures": ev.attendee_count or 0,
            "teacher_present": True,
            "status": ev.get_status_display(),
            "pk": ev.pk,
        })

    total_sessions_count = len(combined_sessions)
    total_exposures_sum = sum(s["total_exposures"] for s in combined_sessions)
    total_boys_sum = sum(s["boys"] for s in combined_sessions)
    total_girls_sum = sum(s["girls"] for s in combined_sessions)

    # Clean schools list
    schools_list = []
    if roster_data and roster_data.get("schools"):
        for sc in roster_data["schools"]:
            b = sc.get("total_boys")
            if b is None and sc.get("divisions"):
                b = sum(d.get("gt", [0, 0, 0])[0] for d in sc["divisions"])
            g = sc.get("total_girls")
            if g is None and sc.get("divisions"):
                g = sum(d.get("gt", [0, 0, 0])[1] for d in sc["divisions"])
            tot_st = sc.get("total_students")
            if not tot_st and sc.get("divisions"):
                tot_st = sum(d.get("gt", [0, 0, 0])[2] for d in sc["divisions"])

            schools_list.append({
                "sl": sc.get("sl"),
                "name": sc.get("name"),
                "taluk": sc.get("taluk") or "—",
                "udise": sc.get("udise") or "—",
                "hm": sc.get("hm") or "",
                "hm_mob": sc.get("hm_mob") or "",
                "teacher": sc.get("teacher") or "",
                "teacher_mob": sc.get("teacher_mob") or "",
                "total_students": tot_st or 0,
                "boys": b or 0,
                "girls": g or 0,
                "school_obj": sc.get("school_obj"),
            })
    elif program.participating_schools.exists():
        for idx, sc in enumerate(program.participating_schools.all(), start=1):
            schools_list.append({
                "sl": idx,
                "name": sc.school_name,
                "taluk": sc.taluk or sc.district or "—",
                "udise": sc.udise_code or "—",
                "hm": sc.headmaster_name or "",
                "hm_mob": sc.headmaster_phone or "",
                "teacher": "",
                "teacher_mob": "",
                "total_students": getattr(sc, "student_strength", 0) or 0,
                "boys": int((getattr(sc, "student_strength", 0) or 0) / 2),
                "girls": int((getattr(sc, "student_strength", 0) or 0) / 2),
                "school_obj": sc,
            })

    total_schools_count = len(schools_list) or program.participating_schools.count()
    total_students_enrolled = sum(sc["total_students"] for sc in schools_list)
    enrolled_boys = sum(sc["boys"] for sc in schools_list)
    enrolled_girls = sum(sc["girls"] for sc in schools_list)
    if roster_data and roster_data.get("kpis"):
        k = roster_data["kpis"]
        if k.get("total_students"):
            total_students_enrolled = k["total_students"]
        if k.get("total_boys"):
            enrolled_boys = k["total_boys"]
        if k.get("total_girls"):
            enrolled_girls = k["total_girls"]

    taluks = sorted(list(set(sc["taluk"] for sc in schools_list if sc["taluk"] and sc["taluk"] != "—")))

    context = {
        "program": program,
        "ev_sessions": ev_sessions,
        "combined_sessions": combined_sessions,
        "total_sessions_count": total_sessions_count,
        "total_exposures_sum": total_exposures_sum,
        "total_boys_sum": total_boys_sum,
        "total_girls_sum": total_girls_sum,
        "schools_list": schools_list,
        "total_schools_count": total_schools_count,
        "total_students_enrolled": total_students_enrolled,
        "enrolled_boys": enrolled_boys,
        "enrolled_girls": enrolled_girls,
        "taluks": taluks,
        "available_projects": available_projects,
        "scholarships": scholarships,
        "internships": internships,
        "mentorship_sessions": mentorship_sessions,
        "roster_data": roster_data,
    }
    return render(request, "programs/program_detail.html", context)


def program_upload_school_roster(request, pk):
    """
    Handles uploading an Excel (.xlsx/.xls) or CSV (.csv) roster for a program,
    persists schools, grade breakdowns, and teacher contacts, and renders
    the updated spreadsheet immediately.
    """
    program = get_object_or_404(Program, pk=pk)
    if request.method == "POST":
        roster_file = request.FILES.get("roster_file")
        if not roster_file:
            messages.error(request, "Please select an Excel (.xlsx/.xls) or CSV (.csv) file to upload.")
            return redirect("programs:program_detail", pk=program.pk)

        ext = os.path.splitext(roster_file.name)[1].lower()
        if ext not in [".xlsx", ".xls", ".csv"]:
            messages.error(request, f"Unsupported file type '{ext}'. Please upload a valid .xlsx, .xls, or .csv file.")
            return redirect("programs:program_detail", pk=program.pk)

        try:
            from .roster import parse_and_save_roster
            res = parse_and_save_roster(program, roster_file)
            school_count = len(res.get("schools", []))
            total_students = res.get("kpis", {}).get("total_students", 0)
            messages.success(
                request,
                f"Successfully parsed and rendered school roster from '{roster_file.name}': {school_count} schools and {total_students:,} students."
            )
        except Exception as e:
            messages.error(request, f"Failed to parse uploaded roster: {e}")

    return redirect("programs:program_detail", pk=program.pk)


def program_remove_school_roster(request, pk):
    """
    Removes the uploaded school roster file, clears participating schools,
    and removes weekly session logs for this program.
    """
    program = get_object_or_404(Program, pk=pk)
    if request.method == "POST":
        from .roster import _get_roster_file_path, _get_roster_cleared_marker_path
        roster_path = _get_roster_file_path(program.pk)
        if os.path.exists(roster_path):
            try:
                os.remove(roster_path)
            except Exception:
                pass

        marker_path = _get_roster_cleared_marker_path(program.pk)
        try:
            with open(marker_path, "w", encoding="utf-8") as f:
                f.write("cleared")
        except Exception:
            pass

        cleared_schools = program.participating_schools.count()
        program.participating_schools.clear()

        from trackers.models import WeeklyTrackerSession
        prog_key = resolve_tracker_programme(program)
        deleted_sessions = 0
        if prog_key:
            deleted_sessions, _ = WeeklyTrackerSession.objects.filter(
                programme=prog_key,
                academic_year=program.academic_year
            ).delete()
        elif program.ngo:
            deleted_sessions, _ = WeeklyTrackerSession.objects.filter(
                ngo=program.ngo,
                academic_year=program.academic_year
            ).delete()

        details = []
        if cleared_schools:
            details.append(f"{cleared_schools} schools detached")
        if deleted_sessions:
            details.append(f"{deleted_sessions} weekly sessions cleared")
        detail_msg = f" ({', '.join(details)})" if details else ""

        messages.success(request, f"Successfully removed uploaded tracking data for '{program.title}'{detail_msg}.")
    return redirect("programs:program_detail", pk=program.pk)


def program_remove_session_logs(request, pk):
    """
    Removes uploaded weekly session logs specifically for this program.
    """
    program = get_object_or_404(Program, pk=pk)
    if request.method == "POST":
        from trackers.models import WeeklyTrackerSession
        prog_key = resolve_tracker_programme(program)
        deleted_sessions = 0
        if prog_key:
            deleted_sessions, _ = WeeklyTrackerSession.objects.filter(
                programme=prog_key,
                academic_year=program.academic_year
            ).delete()
        elif program.participating_schools.exists():
            deleted_sessions, _ = WeeklyTrackerSession.objects.filter(
                school__in=program.participating_schools.all(),
                academic_year=program.academic_year
            ).delete()
        elif program.ngo:
            deleted_sessions, _ = WeeklyTrackerSession.objects.filter(
                ngo=program.ngo,
                academic_year=program.academic_year
            ).delete()

        messages.success(request, f"Successfully removed {deleted_sessions:,} weekly session logs for program '{program.title}'.")

    return redirect(f"{reverse('programs:program_detail', kwargs={'pk': program.pk})}#sessions")


def program_upload_session_log(request, pk):
    """
    Handles Weekly Session Log Excel file upload (.xlsx/.xls) specifically for an individual program.
    Parses session records, persists them to WeeklyTrackerSession, associates them with the program's
    participating schools and partner NGO, and redirects back to the program detail page.
    """
    program = get_object_or_404(
        Program.objects.select_related("ngo", "project").prefetch_related("participating_schools"),
        pk=pk
    )
    if request.method != "POST":
        return redirect("programs:program_detail", pk=program.pk)

    uploaded_file = request.FILES.get("session_log_file") or request.FILES.get("file")
    academic_year = request.POST.get("academic_year", program.academic_year).strip()
    target_ngo = program.ngo or (program.project.ngo if program.project else None)
    target_ngo_code = request.POST.get("ngo_code", "").strip() or (target_ngo.code if target_ngo else None)

    if not uploaded_file:
        messages.error(request, "Please select an Excel (.xlsx or .xls) file containing weekly session logs to upload.")
        return redirect(f"{reverse('programs:program_detail', kwargs={'pk': program.pk})}#sessions")

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in [".xlsx", ".xls"]:
        messages.error(request, f"Unsupported file type '{ext}'. Please upload a valid .xlsx or .xls Excel file.")
        return redirect(f"{reverse('programs:program_detail', kwargs={'pk': program.pk})}#sessions")

    try:
        from .roster import _get_roster_cleared_marker_path
        marker_path = _get_roster_cleared_marker_path(program.pk)
        if os.path.exists(marker_path):
            try:
                os.remove(marker_path)
            except Exception:
                pass

        from trackers.services.excel_importer import import_yfs_workbook
        prog_key = resolve_tracker_programme(program)

        res = import_yfs_workbook(
            uploaded_file,
            academic_year=academic_year,
            ngo_code=target_ngo_code,
            target_program=program,
            target_programme=prog_key,
        )

        sess_count = res.get("sessions_imported", 0)
        if sess_count > 0:
            messages.success(
                request,
                f"Successfully added {sess_count:,} weekly session logs from '{uploaded_file.name}' "
                f"for program '{program.title}' ({res.get('total_exposures', 0):,} student exposures across {res.get('schools_count', 0)} schools)."
            )
        else:
            messages.warning(
                request,
                f"Uploaded workbook '{uploaded_file.name}' was parsed for AY {academic_year}, but no weekly session rows could be extracted. "
                "Ensure the sheet contains standard weekly session columns (Month, Day, School/Venue, Standard, Topic, Instructor, Boys, Girls, Total Exposures)."
            )
    except Exception as e:
        messages.error(request, f"Failed to ingest Weekly Session Log Excel file: {e}")

    return redirect(f"{reverse('programs:program_detail', kwargs={'pk': program.pk})}#sessions")



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

    context = {
        "ngo": ngo,
        "current_ngo": ngo,
        "requested_ngo": ngo.code.lower(),
        "schools": schools,
        "total_students": total_students,
        "programs": programs,
        "ev_sessions": ev_sessions,
        "allocated_resources": allocated_resources,
        "foundation_subtab": "dossier",
    }
    if ngo.code in ["PRATHAM", "AGASTYA", "YFS"]:
        from trackers.views import get_ngo_nav
        context["ngo_nav"] = get_ngo_nav(ngo)

    return render(request, "programs/ngo_detail.html", context)


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
    category_tab = request.GET.get("tab") or request.GET.get("category") or "all"
    if category_tab in ["propen", "mike_propen"]:
        return redirect("programs:propen_portal")

    status_filter = request.GET.get("status")
    search_query = request.GET.get("q", "").strip()

    all_queryset = Scholarship.objects.filter(is_archived=False)
    gov_count = all_queryset.filter(category=Scholarship.Category.GOVERNMENT).count()
    emp_count = all_queryset.filter(category=Scholarship.Category.EMPLOYEE_SPECIAL).count()
    fnd_count = all_queryset.filter(category=Scholarship.Category.FOUNDATION).count()
    propen_count = MikePropenScholarshipApplication.objects.count()
    all_count = all_queryset.count()

    queryset = all_queryset.select_related("student", "student__school", "project", "program")

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

    # Foundation section data (Feature 5)
    foundation_stats = {}
    if category_tab == "foundation":
        foundation_stats = {
            "csr_grants": CSRGrant.objects.select_related("school", "project").order_by("-created_at")[:10],
            "csr_total": CSRGrant.objects.aggregate(Sum("grant_amount"))["grant_amount__sum"] or 0,
            "mentorship_count": MentorshipSession.objects.count(),
            "mentorship_recent": MentorshipSession.objects.select_related("student", "project", "program").order_by("-session_date")[:5],
        }

    return render(
        request,
        "programs/scholarship_list.html",
        {
            "scholarships": queryset,
            "active_tab": category_tab,
            "selected_tab": category_tab,
            "active_page": "scholarships",
            "total_count": all_count,
            "filtered_count": queryset.count(),
            "total_sanctioned": total_sanctioned,
            "total_disbursed": total_disbursed,
            "gov_count": gov_count,
            "emp_count": emp_count,
            "fnd_count": fnd_count,
            "propen_count": propen_count,
            "foundation_count": fnd_count,
            "status_choices": Scholarship.Status.choices,
            "selected_status": status_filter,
            "search_query": search_query,
            **foundation_stats,
        },
    )


def scholarship_create(request):
    raw_cat = request.GET.get("category", Scholarship.Category.FOUNDATION).upper()
    category = raw_cat if raw_cat in dict(Scholarship.Category.choices) else Scholarship.Category.FOUNDATION
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


# ============================================================================
# INDUSTRY VISITS (Feature 11)
# ============================================================================

def industry_visit_list(request):
    q = request.GET.get("q", "").strip()
    visits = IndustryVisit.objects.filter(is_archived=False).select_related("school", "program", "project")
    if q:
        visits = visits.filter(
            Q(title__icontains=q) | Q(company_name__icontains=q) | Q(visit_code__icontains=q) | Q(location__icontains=q)
        )
    return render(request, "programs/industry_visit_list.html", {
        "visits": visits,
        "query": q,
        "active_page": "industry_visits",
    })


def industry_visit_create(request):
    if request.method == "POST":
        form = IndustryVisitForm(request.POST)
        if form.is_valid():
            visit = form.save()
            messages.success(request, f"Industry Visit '{visit.title}' ({visit.visit_code}) created.")
            return redirect("programs:industry_visit_list")
    else:
        form = IndustryVisitForm()
    return render(request, "programs/industry_visit_form.html", {
        "form": form,
        "is_edit": False,
        "title": "Schedule Industry Visit",
        "active_page": "industry_visits",
    })


def industry_visit_detail(request, pk):
    visit = get_object_or_404(IndustryVisit, pk=pk)
    return render(request, "programs/industry_visit_detail.html", {
        "visit": visit,
        "active_page": "industry_visits",
    })


def industry_visit_edit(request, pk):
    visit = get_object_or_404(IndustryVisit, pk=pk)
    if request.method == "POST":
        form = IndustryVisitForm(request.POST, instance=visit)
        if form.is_valid():
            visit = form.save()
            messages.success(request, f"Industry Visit '{visit.title}' updated.")
            return redirect("programs:industry_visit_list")
    else:
        form = IndustryVisitForm(instance=visit)
    return render(request, "programs/industry_visit_form.html", {
        "form": form,
        "visit": visit,
        "is_edit": True,
        "title": f"Edit: {visit.visit_code}",
        "active_page": "industry_visits",
    })


def industry_visit_toggle_archive(request, pk):
    visit = get_object_or_404(IndustryVisit, pk=pk)
    if request.method == "POST":
        visit.is_archived = not visit.is_archived
        visit.save(update_fields=["is_archived"])
        action = "archived" if visit.is_archived else "restored"
        messages.success(request, f"Industry Visit '{visit.visit_code}' {action}.")
    return redirect("programs:industry_visit_list")


# ============================================================================
# BULK UPLOAD: SCHOLARSHIPS (Feature 2 / 9)
# ============================================================================

SCHOLARSHIP_HEADER_ALIASES = {
    "admission_no": "admission_number",
    "adm_no": "admission_number",
    "admission_num": "admission_number",
    "student_id": "admission_number",
    "student": "student_name",
    "student_name": "student_name",
    "name": "student_name",
    "amount": "sanctioned_amount",
    "sanctioned": "sanctioned_amount",
    "sanctioned_amount": "sanctioned_amount",
    "scholarship_amount": "sanctioned_amount",
    "disbursed": "disbursed_amount",
    "disbursed_amount": "disbursed_amount",
    "paid_amount": "disbursed_amount",
    "category": "category",
    "scholarship_type": "category",
    "type": "category",
    "scheme": "scheme_name",
    "scheme_name": "scheme_name",
    "scholarship": "scheme_name",
    "scholarship_name": "scheme_name",
    "year": "academic_year",
    "academic_year": "academic_year",
    "application_no": "application_number",
    "application_number": "application_number",
    "app_no": "application_number",
    "emp_code": "employee_code",
    "employee_code": "employee_code",
    "emp_name": "employee_name",
    "employee_name": "employee_name",
    "emp_dept": "employee_department",
    "employee_department": "employee_department",
    "department": "employee_department",
    "plant": "plant_location",
    "location": "plant_location",
    "plant_location": "plant_location",
    "status": "status",
    "remarks": "remarks",
}


def _normalize_header(name):
    from backend.utils import normalize_header
    return normalize_header(name, SCHOLARSHIP_HEADER_ALIASES)


def bulk_upload_scholarships(request):
    from backend.utils import parse_decimal_clean
    if request.method != "POST":
        return render(request, "programs/scholarship_bulk_upload.html", {"active_page": "scholarships"})

    uploaded_file = request.FILES.get("file") or request.FILES.get("csv_file")
    if not uploaded_file:
        messages.error(request, "Please select a CSV or Excel (.xlsx) file.")
        return redirect("programs:scholarship_bulk_upload")

    file_name = uploaded_file.name.lower()
    if not file_name.endswith((".csv", ".xlsx", ".xls")):
        messages.error(request, "Only CSV and Excel (.xlsx, .xls) files are supported.")
        return redirect("programs:scholarship_bulk_upload")

    try:
        if file_name.endswith(".csv"):
            decoded = uploaded_file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(decoded))
            reader.fieldnames = [_normalize_header(f) for f in (reader.fieldnames or [])]
            rows = list(reader)
        else:
            import openpyxl
            wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
            ws = wb.active
            excel_rows = list(ws.iter_rows(values_only=True))
            wb.close()
            if not excel_rows:
                messages.error(request, "The Excel file is empty.")
                return redirect("programs:scholarship_bulk_upload")
            headers = [_normalize_header(c) for c in excel_rows[0]]
            rows = []
            for r in excel_rows[1:]:
                if not any(c is not None and str(c).strip() for c in r):
                    continue
                row_dict = {}
                for i in range(len(headers)):
                    if headers[i]:
                        row_dict[headers[i]] = str(r[i]).strip() if i < len(r) and r[i] is not None else ""
                rows.append(row_dict)

        created, skipped, errors = 0, 0, []
        with transaction.atomic():
            for idx, row in enumerate(rows, start=2):
                admission = str(row.get("admission_number") or "").strip()
                s_name = str(row.get("student_name") or "").strip()

                student = None
                if admission:
                    student = Student.objects.filter(admission_number__iexact=admission).first()
                if not student and s_name:
                    student = Student.objects.filter(student_name__iexact=s_name).first() or Student.objects.filter(student_name__icontains=s_name).first()

                if not student:
                    errors.append(f"Row {idx}: Student '{admission or s_name}' not found")
                    continue

                app_num = str(row.get("application_number") or "").strip()
                if not app_num:
                    app_num = f"BULK-{timezone.now().strftime('%Y%m%d')}-{idx:04d}"
                if Scholarship.objects.filter(application_number=app_num).exists():
                    skipped += 1
                    continue

                sanctioned = parse_decimal_clean(row.get("sanctioned_amount"), default=Decimal("0"))
                disbursed = parse_decimal_clean(row.get("disbursed_amount"), default=Decimal("0"))

                category = str(row.get("category") or "FOUNDATION").strip().upper() or "FOUNDATION"
                status = str(row.get("status") or "APPLIED").strip().upper() or "APPLIED"

                Scholarship.objects.create(
                    student=student,
                    category=category,
                    scheme_name=str(row.get("scheme_name") or "Bulk Upload Scholarship").strip(),
                    application_number=app_num,
                    academic_year=str(row.get("academic_year") or "2026-27").strip() or "2026-27",
                    sanctioned_amount=sanctioned,
                    disbursed_amount=disbursed,
                    status=status,
                    employee_code=str(row.get("employee_code") or "").strip(),
                    employee_name=str(row.get("employee_name") or "").strip(),
                    employee_department=str(row.get("employee_department") or "").strip(),
                    plant_location=str(row.get("plant_location") or "Belagavi SEZ").strip(),
                    remarks=str(row.get("remarks") or "").strip(),
                )
                created += 1

        msg = f"Bulk upload complete: {created} scholarships created"
        if skipped:
            msg += f", {skipped} skipped (duplicate)"
        if errors:
            msg += f", {len(errors)} errors"
        messages.success(request, msg)
        if errors:
            for e in errors[:10]:
                messages.warning(request, e)

    except Exception as exc:
        messages.error(request, f"Upload failed: {exc}")

    return redirect("programs:scholarship_bulk_upload")

