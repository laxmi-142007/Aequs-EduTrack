import csv
import json
from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q

from .models import (
    InternshipProgram,
    InternshipPlacement,
    InternshipMilestone,
    InternshipDocument,
    Department,
)

from .forms import InternshipDocumentForm

from .services import (
    get_internship_kpis,
    generate_certificate_number,
    get_eligible_students_for_internship,
    seed_internship_demo_data,
    is_internship_eligible_class,
)

from students.models import Student
from schools.models import School

from eligibility.models import EligibilityRecord, BenefitType


# =============================================================================
# SERIALIZERS / HELPERS
# =============================================================================

def _placement_to_dict(p):
    return {
        "id": p.id,
        "student_id": p.student.id,
        "student_name": p.student.student_name,
        "admission_number": p.student.admission_number,
        "student_class": p.student.current_class,
        "student_gender": p.student.gender,
        "student_phone": (
            p.student.student_phone
            or p.student.parent_phone
            or ""
        ),
        "school_id": (
            p.school.id
            if p.school
            else (
                p.student.school.id
                if p.student.school
                else None
            )
        ),
        "school_name": (
            p.school.name
            if p.school
            else (
                p.student.school.name
                if p.student.school
                else "General"
            )
        ),
        "school_district": (
            p.school.district
            if p.school
            else (
                p.student.school.district
                if p.student.school
                else ""
            )
        ),
        "program_id": p.program.id if p.program else None,
        "program_title": (
            p.program.title
            if p.program
            else "Direct Placement"
        ),
        "program_code": (
            p.program.program_code
            if p.program
            else ""
        ),
        "department": p.department,
        "department_display": p.get_department_display(),
        "company_name": p.company_name,
        "project_title": (
            p.project_title
            or (
                p.program.title
                if p.program
                else "Industrial Internship"
            )
        ),
        "academic_year": p.academic_year,
        "start_date": (
            p.start_date.strftime("%Y-%m-%d")
            if p.start_date
            else ""
        ),
        "end_date": (
            p.end_date.strftime("%Y-%m-%d")
            if p.end_date
            else ""
        ),
        "stipend_amount": float(p.stipend_amount),
        "mentor_name": (
            p.mentor_name
            or (
                p.program.mentor_in_charge
                if p.program
                else ""
            )
        ),
        "mentor_email": (
            p.mentor_email
            or (
                p.program.mentor_contact
                if p.program
                else ""
            )
        ),
        "mentor_phone": p.mentor_phone or "",
        "status": p.status,
        "status_display": p.get_status_display(),
        "attendance_percentage": (
            float(p.attendance_percentage)
            if p.attendance_percentage is not None
            else 100.0
        ),
        "performance_grade": p.performance_grade,
        "performance_grade_display": (
            p.get_performance_grade_display()
        ),
        "certificate_issued": p.certificate_issued,
        "certificate_number": p.certificate_number or "",
        "certificate_issue_date": (
            p.certificate_issue_date.strftime("%Y-%m-%d")
            if p.certificate_issue_date
            else ""
        ),
        "evaluation_feedback": (
            p.evaluation_feedback or ""
        ),
        "milestones_count": p.milestones.count(),
        "created_at": p.created_at.strftime(
            "%Y-%m-%d %H:%M"
        ),
    }


def _program_to_dict(prog):
    return {
        "id": prog.id,
        "title": prog.title,
        "program_code": prog.program_code,
        "company_name": prog.company_name,
        "department": prog.department,
        "department_display": prog.get_department_display(),
        "location": prog.location,
        "duration_months": prog.duration_months,
        "stipend_amount": float(prog.stipend_amount),
        "total_slots": prog.total_slots,
        "enrolled_count": prog.enrolled_count,
        "available_slots": prog.available_slots,
        "academic_year": prog.academic_year,
        "start_date": (
            prog.start_date.strftime("%Y-%m-%d")
            if prog.start_date
            else ""
        ),
        "end_date": (
            prog.end_date.strftime("%Y-%m-%d")
            if prog.end_date
            else ""
        ),
        "eligibility_criteria": prog.eligibility_criteria,
        "description": prog.description,
        "mentor_in_charge": prog.mentor_in_charge,
        "mentor_contact": prog.mentor_contact,
        "status": prog.status,
        "status_display": prog.get_status_display(),
        "created_at": prog.created_at.strftime(
            "%Y-%m-%d"
        ),
    }


def _document_to_dict(document):
    """
    Convert an InternshipDocument instance into JSON-safe data.
    """

    return {
        "id": document.id,
        "placement_id": document.placement_id,
        "document_type": document.document_type,
        "document_type_display": (
            document.get_document_type_display()
        ),
        "file_name": (
            document.document.name.split("/")[-1]
            if document.document
            else ""
        ),
        "file_url": (
            document.document.url
            if document.document
            else ""
        ),
        "uploaded_at": (
            document.uploaded_at.strftime(
                "%Y-%m-%d %H:%M"
            )
            if document.uploaded_at
            else ""
        ),
    }


# =============================================================================
# MAIN INTERNSHIP PORTAL
# =============================================================================

@ensure_csrf_cookie
def internship_portal(request):
    """
    Main Internship Management Portal.
    """

    seed_internship_demo_data()

    kpis = get_internship_kpis()

    programs = (
        InternshipProgram.objects
        .all()
        .order_by("-created_at")
    )

    schools = (
        School.objects
        .filter(status=School.Status.ACTIVE)
        .order_by("name")
    )

    all_active_students = (
        Student.objects
        .filter(status=Student.Status.ACTIVE)
        .select_related("school")
        .order_by("student_name")
    )

    students = [
        student
        for student in all_active_students
        if is_internship_eligible_class(
            student.current_class
        )
    ]

    departments = Department.choices

    status_choices = InternshipPlacement.Status.choices

    grade_choices = InternshipPlacement.PerformanceGrade.choices

    program_statuses = InternshipProgram.Status.choices

    context = {
        "kpis": kpis,
        "programs": programs,
        "schools": schools,
        "students": students,
        "departments": departments,
        "status_choices": status_choices,
        "grade_choices": grade_choices,
        "program_statuses": program_statuses,

        # Also make document choices available to the portal
        # in case the upload modal is located there.
        "document_type_choices": (
            InternshipDocument.DocumentType.choices
        ),
    }

    return render(
        request,
        "internships/portal.html",
        context,
    )


# =============================================================================
# INTERNSHIP DOCUMENTS
# =============================================================================

@require_http_methods(["GET", "POST"])
def internship_documents(request, placement_id=None):
    """
    Display and upload documents for an internship placement.

    GET:
        Displays the student's internship documents.

    POST:
        Uploads a document for the selected placement.
    """

    # -------------------------------------------------------------------------
    # Determine placement
    # -------------------------------------------------------------------------

    if placement_id is None:
        placement_id = request.POST.get("placement_id")

    if not placement_id:
        return JsonResponse(
            {
                "success": False,
                "error": "Internship placement is required.",
            },
            status=400,
        )

    placement = get_object_or_404(
        InternshipPlacement.objects.select_related(
            "student",
            "school",
            "program",
        ),
        id=placement_id,
    )

    # -------------------------------------------------------------------------
    # POST - Upload document
    # -------------------------------------------------------------------------

    if request.method == "POST":

        form = InternshipDocumentForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            document = form.save(commit=False)

            document.placement = placement

            document.save()

            if (
                request.headers.get("X-Requested-With")
                == "XMLHttpRequest"
            ):
                return JsonResponse(
                    {
                        "success": True,
                        "message": (
                            "Document uploaded successfully."
                        ),
                        "document": _document_to_dict(
                            document
                        ),
                    }
                )

            return redirect(
                "internships:documents",
                placement_id=placement.id,
            )

    else:
        form = InternshipDocumentForm()

    # -------------------------------------------------------------------------
    # Existing documents
    # -------------------------------------------------------------------------

    documents = (
        InternshipDocument.objects
        .filter(placement=placement)
        .order_by("-uploaded_at")
    )

    # -------------------------------------------------------------------------
    # Required document types
    # -------------------------------------------------------------------------
    #
    # IMPORTANT:
    # These values MUST exactly match the values in
    # InternshipDocument.DocumentType.
    #

    required_document_types = [
        {
            "value": InternshipDocument.DocumentType.RESUME,
            "label": "Resume",
        },
        {
            "value": InternshipDocument.DocumentType.AADHAAR,
            "label": "Aadhaar Card",
        },
        {
            "value": InternshipDocument.DocumentType.PAN,
            "label": "PAN Card",
        },
        {
            "value": InternshipDocument.DocumentType.COLLEGE_ID,
            "label": "College ID",
        },
        {
            "value": InternshipDocument.DocumentType.BONAFIDE,
            "label": "Bonafide Certificate",
        },
        {
            "value": InternshipDocument.DocumentType.MARKSHEET,
            "label": "Marksheet",
        },
        {
            "value": InternshipDocument.DocumentType.OFFER_LETTER,
            "label": "Offer Letter",
        },
        {
            "value": InternshipDocument.DocumentType.OTHER,
            "label": "Other Document",
        },
    ]

    uploaded_type_values = set(
        documents.values_list(
            "document_type",
            flat=True,
        )
    )

    for item in required_document_types:
        item["uploaded"] = (
            item["value"] in uploaded_type_values
        )

    # -------------------------------------------------------------------------
    # IMPORTANT:
    # Send the choices separately as well.
    #
    # This allows the HTML template to build the dropdown directly,
    # even if there is a problem with form rendering.
    # -------------------------------------------------------------------------

    document_type_choices = (
        InternshipDocument.DocumentType.choices
    )

    # -------------------------------------------------------------------------
    # Render
    # -------------------------------------------------------------------------

    return render(
        request,
        "internships/documents.html",
        {
            "placement": placement,
            "student": placement.student,
            "documents": documents,
            "form": form,

            # Required document cards/list
            "required_document_types": (
                required_document_types
            ),

            # Direct dropdown choices
            "document_type_choices": (
                document_type_choices
            ),

            # Useful aliases for templates
            "document_types": (
                document_type_choices
            ),
        },
    )


# =============================================================================
# DOCUMENT DOWNLOAD
# =============================================================================

def download_internship_document(
    request,
    document_id,
):
    """
    Download an uploaded internship document.
    """

    document = get_object_or_404(
        InternshipDocument,
        id=document_id,
    )

    if not document.document:
        return JsonResponse(
            {
                "success": False,
                "error": "Document file not found.",
            },
            status=404,
        )

    try:
        response = FileResponse(
            document.document.open("rb"),
            as_attachment=True,
            filename=(
                document.document.name.split("/")[-1]
            ),
        )

        return response

    except FileNotFoundError:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "The uploaded file could not be found."
                ),
            },
            status=404,
        )


# =============================================================================
# DOCUMENT DELETE
# =============================================================================

@require_http_methods(["POST", "DELETE"])
def delete_internship_document(
    request,
    document_id,
):
    """
    Delete an internship document.
    """

    document = get_object_or_404(
        InternshipDocument,
        id=document_id,
    )

    placement_id = document.placement_id

    document.delete()

    if (
        request.headers.get("X-Requested-With")
        == "XMLHttpRequest"
    ):
        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Document deleted successfully."
                ),
            }
        )

    return redirect(
        "internships:documents",
        placement_id=placement_id,
    )


# =============================================================================
# REST APIs - PLACEMENTS / INTERNS
# =============================================================================

def api_internships(request):

    search = request.GET.get("q", "").strip()

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    dept_filter = request.GET.get(
        "department",
        "",
    ).strip()

    program_id = request.GET.get(
        "program_id",
        "",
    ).strip()

    school_id = request.GET.get(
        "school_id",
        "",
    ).strip()

    academic_year = request.GET.get(
        "academic_year",
        "",
    ).strip()

    qs = (
        InternshipPlacement.objects
        .select_related(
            "student",
            "school",
            "program",
            "student__school",
        )
        .prefetch_related("milestones")
        .all()
    )

    if search:
        qs = qs.filter(
            Q(student__student_name__icontains=search)
            | Q(
                student__admission_number__icontains=search
            )
            | Q(project_title__icontains=search)
            | Q(company_name__icontains=search)
            | Q(mentor_name__icontains=search)
            | Q(
                certificate_number__icontains=search
            )
        )

    if status_filter:
        qs = qs.filter(status=status_filter)

    if dept_filter:
        qs = qs.filter(department=dept_filter)

    if program_id:
        qs = qs.filter(program_id=program_id)

    if school_id:
        qs = qs.filter(
            Q(school_id=school_id)
            | Q(student__school_id=school_id)
        )

    if academic_year:
        qs = qs.filter(
            academic_year=academic_year
        )

    placements = [
        _placement_to_dict(p)
        for p in qs
    ]

    return JsonResponse(
        {
            "success": True,
            "count": len(placements),
            "results": placements,
        }
    )


# =============================================================================
# CREATE INTERNSHIP
# =============================================================================

@require_http_methods(["POST"])
def api_create_internship(request):

    try:

        data = (
            json.loads(
                request.body.decode("utf-8")
            )
            if request.body
            else request.POST
        )

        student_id = data.get("student_id")

        if not student_id:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Student is required.",
                },
                status=400,
            )

        student = get_object_or_404(
            Student,
            id=student_id,
        )

        if not is_internship_eligible_class(
            student.current_class
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        f"Student "
                        f"({student.student_name} - "
                        f"{student.current_class}) "
                        f"is not eligible for "
                        f"corporate internships."
                    ),
                },
                status=400,
            )

        program_id = data.get("program_id")

        program = (
            get_object_or_404(
                InternshipProgram,
                id=program_id,
            )
            if program_id
            else None
        )

        school = student.school

        dept = (
            data.get("department")
            or (
                program.department
                if program
                else Department.PRECISION_MANUFACTURING
            )
        )

        company = (
            data.get("company_name")
            or (
                program.company_name
                if program
                else "Aequs Aerospace SEZ"
            )
        )

        stipend = Decimal(
            str(
                data.get("stipend_amount")
                or (
                    program.stipend_amount
                    if program
                    else 8000.00
                )
            )
        )

        academic_year = (
            data.get("academic_year")
            or "2026-27"
        )

        start_date_str = data.get("start_date")

        start_date = (
            timezone.datetime.strptime(
                start_date_str,
                "%Y-%m-%d",
            ).date()
            if start_date_str
            else timezone.localdate()
        )

        end_date_str = data.get("end_date")

        end_date = (
            timezone.datetime.strptime(
                end_date_str,
                "%Y-%m-%d",
            ).date()
            if end_date_str
            else None
        )

        placement = InternshipPlacement.objects.create(
            student=student,
            program=program,
            school=school,
            department=dept,
            company_name=company,
            project_title=(
                data.get(
                    "project_title",
                    "",
                )
                or (
                    program.title
                    if program
                    else "Industrial Internship"
                )
            ),
            academic_year=academic_year,
            start_date=start_date,
            end_date=end_date,
            stipend_amount=stipend,
            mentor_name=(
                data.get("mentor_name", "")
                or (
                    program.mentor_in_charge
                    if program
                    else ""
                )
            ),
            mentor_email=(
                data.get("mentor_email", "")
                or (
                    program.mentor_contact
                    if program
                    else ""
                )
            ),
            mentor_phone=data.get(
                "mentor_phone",
                "",
            ),
            status=data.get(
                "status",
                InternshipPlacement.Status.SELECTED,
            ),
            attendance_percentage=Decimal(
                str(
                    data.get(
                        "attendance_percentage",
                        100.0,
                    )
                )
            ),
            performance_grade=data.get(
                "performance_grade",
                InternshipPlacement.PerformanceGrade.PENDING,
            ),
            evaluation_feedback=data.get(
                "evaluation_feedback",
                "",
            ),
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Internship placement "
                    "created successfully."
                ),
                "placement": _placement_to_dict(
                    placement
                ),
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# =============================================================================
# UPDATE INTERNSHIP
# =============================================================================

@require_http_methods(["POST"])
def api_update_internship(
    request,
    placement_id,
):

    try:

        placement = get_object_or_404(
            InternshipPlacement,
            id=placement_id,
        )

        data = (
            json.loads(
                request.body.decode("utf-8")
            )
            if request.body
            else request.POST
        )

        if "department" in data:
            placement.department = data[
                "department"
            ]

        if "company_name" in data:
            placement.company_name = data[
                "company_name"
            ]

        if "project_title" in data:
            placement.project_title = data[
                "project_title"
            ]

        if "academic_year" in data:
            placement.academic_year = data[
                "academic_year"
            ]

        if (
            "start_date" in data
            and data["start_date"]
        ):
            placement.start_date = (
                timezone.datetime.strptime(
                    data["start_date"],
                    "%Y-%m-%d",
                ).date()
            )

        if "end_date" in data:
            placement.end_date = (
                timezone.datetime.strptime(
                    data["end_date"],
                    "%Y-%m-%d",
                ).date()
                if data["end_date"]
                else None
            )

        if (
            "stipend_amount" in data
            and data["stipend_amount"] is not None
        ):
            placement.stipend_amount = Decimal(
                str(data["stipend_amount"])
            )

        if "mentor_name" in data:
            placement.mentor_name = data[
                "mentor_name"
            ]

        if "mentor_email" in data:
            placement.mentor_email = data[
                "mentor_email"
            ]

        if "mentor_phone" in data:
            placement.mentor_phone = data[
                "mentor_phone"
            ]

        if "status" in data:
            placement.status = data["status"]

        if (
            "attendance_percentage" in data
            and data["attendance_percentage"]
            is not None
        ):
            placement.attendance_percentage = Decimal(
                str(
                    data[
                        "attendance_percentage"
                    ]
                )
            )

        if "performance_grade" in data:
            placement.performance_grade = data[
                "performance_grade"
            ]

        if "evaluation_feedback" in data:
            placement.evaluation_feedback = data[
                "evaluation_feedback"
            ]

        if (
            data.get("issue_certificate") is True
            or (
                placement.status
                == InternshipPlacement.Status.COMPLETED
                and data.get("certificate_issued")
                is True
            )
        ):

            placement.certificate_issued = True

            if not placement.certificate_number:
                placement.certificate_number = (
                    generate_certificate_number(
                        placement
                    )
                )

            if not placement.certificate_issue_date:
                placement.certificate_issue_date = (
                    timezone.localdate()
                )

        placement.save()

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Placement updated successfully."
                ),
                "placement": _placement_to_dict(
                    placement
                ),
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# =============================================================================
# UPDATE STATUS
# =============================================================================

@require_http_methods(["POST"])
def api_update_status(
    request,
    placement_id,
):

    try:

        placement = get_object_or_404(
            InternshipPlacement,
            id=placement_id,
        )

        data = (
            json.loads(
                request.body.decode("utf-8")
            )
            if request.body
            else request.POST
        )

        new_status = data.get("status")

        if not new_status:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Status is required.",
                },
                status=400,
            )

        placement.status = new_status

        if "performance_grade" in data:
            placement.performance_grade = data[
                "performance_grade"
            ]

        if "evaluation_feedback" in data:
            placement.evaluation_feedback = data[
                "evaluation_feedback"
            ]

        if (
            new_status
            == InternshipPlacement.Status.COMPLETED
            or data.get("issue_certificate")
        ):

            placement.certificate_issued = True

            if not placement.certificate_number:
                placement.certificate_number = (
                    generate_certificate_number(
                        placement
                    )
                )

            if not placement.certificate_issue_date:
                placement.certificate_issue_date = (
                    timezone.localdate()
                )

        placement.save()

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"Status updated to "
                    f"{placement.get_status_display()}."
                ),
                "placement": _placement_to_dict(
                    placement
                ),
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# =============================================================================
# DELETE INTERNSHIP
# =============================================================================

@require_http_methods(["POST"])
def api_delete_internship(
    request,
    placement_id,
):

    try:

        placement = get_object_or_404(
            InternshipPlacement,
            id=placement_id,
        )

        placement.delete()

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Internship placement "
                    "removed successfully."
                ),
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# =============================================================================
# PROGRAMS
# =============================================================================

def api_programs(request):

    programs = (
        InternshipProgram.objects
        .all()
        .order_by("-created_at")
    )

    results = [
        _program_to_dict(p)
        for p in programs
    ]

    return JsonResponse(
        {
            "success": True,
            "count": len(results),
            "results": results,
        }
    )


# =============================================================================
# CREATE PROGRAM
# =============================================================================

@require_http_methods(["POST"])
def api_create_program(request):

    try:

        data = (
            json.loads(
                request.body.decode("utf-8")
            )
            if request.body
            else request.POST
        )

        title = data.get(
            "title",
            "",
        ).strip()

        code = data.get(
            "program_code",
            "",
        ).strip()

        if not title or not code:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Title and Program Code "
                        "are required."
                    ),
                },
                status=400,
            )

        start_date = (
            timezone.datetime.strptime(
                data["start_date"],
                "%Y-%m-%d",
            ).date()
            if data.get("start_date")
            else None
        )

        end_date = (
            timezone.datetime.strptime(
                data["end_date"],
                "%Y-%m-%d",
            ).date()
            if data.get("end_date")
            else None
        )

        prog = InternshipProgram.objects.create(
            title=title,
            program_code=code,
            company_name=data.get(
                "company_name",
                "Aequs Aerospace SEZ",
            ),
            department=data.get(
                "department",
                Department.PRECISION_MANUFACTURING,
            ),
            location=data.get(
                "location",
                "Belagavi SEZ, Karnataka",
            ),
            duration_months=int(
                data.get(
                    "duration_months",
                    3,
                )
            ),
            stipend_amount=Decimal(
                str(
                    data.get(
                        "stipend_amount",
                        8000.00,
                    )
                )
            ),
            total_slots=int(
                data.get(
                    "total_slots",
                    15,
                )
            ),
            academic_year=data.get(
                "academic_year",
                "2026-27",
            ),
            start_date=start_date,
            end_date=end_date,
            eligibility_criteria=data.get(
                "eligibility_criteria",
                "",
            ),
            description=data.get(
                "description",
                "",
            ),
            mentor_in_charge=data.get(
                "mentor_in_charge",
                "",
            ),
            mentor_contact=data.get(
                "mentor_contact",
                "",
            ),
            status=data.get(
                "status",
                InternshipProgram.Status.OPEN,
            ),
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Internship track "
                    "created successfully."
                ),
                "program": _program_to_dict(
                    prog
                ),
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# =============================================================================
# UPDATE PROGRAM
# =============================================================================

@require_http_methods(["POST"])
def api_update_program(
    request,
    program_id,
):

    try:

        prog = get_object_or_404(
            InternshipProgram,
            id=program_id,
        )

        data = (
            json.loads(
                request.body.decode("utf-8")
            )
            if request.body
            else request.POST
        )

        if "title" in data:
            prog.title = data["title"]

        if "company_name" in data:
            prog.company_name = data[
                "company_name"
            ]

        if "department" in data:
            prog.department = data[
                "department"
            ]

        if "location" in data:
            prog.location = data[
                "location"
            ]

        if "duration_months" in data:
            prog.duration_months = int(
                data["duration_months"]
            )

        if "stipend_amount" in data:
            prog.stipend_amount = Decimal(
                str(
                    data["stipend_amount"]
                )
            )

        if "total_slots" in data:
            prog.total_slots = int(
                data["total_slots"]
            )

        if "academic_year" in data:
            prog.academic_year = data[
                "academic_year"
            ]

        if "start_date" in data:
            prog.start_date = (
                timezone.datetime.strptime(
                    data["start_date"],
                    "%Y-%m-%d",
                ).date()
                if data["start_date"]
                else None
            )

        if "end_date" in data:
            prog.end_date = (
                timezone.datetime.strptime(
                    data["end_date"],
                    "%Y-%m-%d",
                ).date()
                if data["end_date"]
                else None
            )

        if "eligibility_criteria" in data:
            prog.eligibility_criteria = data[
                "eligibility_criteria"
            ]

        if "description" in data:
            prog.description = data[
                "description"
            ]

        if "mentor_in_charge" in data:
            prog.mentor_in_charge = data[
                "mentor_in_charge"
            ]

        if "mentor_contact" in data:
            prog.mentor_contact = data[
                "mentor_contact"
            ]

        if "status" in data:
            prog.status = data["status"]

        prog.save()

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Program updated successfully."
                ),
                "program": _program_to_dict(
                    prog
                ),
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# =============================================================================
# DELETE PROGRAM
# =============================================================================

@require_http_methods(["POST"])
def api_delete_program(
    request,
    program_id,
):

    try:

        prog = get_object_or_404(
            InternshipProgram,
            id=program_id,
        )

        prog.delete()

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Program removed successfully."
                ),
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# =============================================================================
# ELIGIBLE CANDIDATES
# =============================================================================

def api_eligible_candidates(request):

    academic_year = request.GET.get(
        "academic_year",
        "2026-27",
    )

    candidates = (
        get_eligible_students_for_internship(
            academic_year
        )
    )

    return JsonResponse(
        {
            "success": True,
            "count": len(candidates),
            "results": candidates,
        }
    )


# =============================================================================
# QUICK ASSIGN CANDIDATE
# =============================================================================

@require_http_methods(["POST"])
def api_quick_assign_candidate(request):

    try:

        data = (
            json.loads(
                request.body.decode("utf-8")
            )
            if request.body
            else request.POST
        )

        student_id = data.get("student_id")

        program_id = data.get("program_id")

        if not student_id or not program_id:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Both student and program "
                        "must be selected."
                    ),
                },
                status=400,
            )

        student = get_object_or_404(
            Student,
            id=student_id,
        )

        program = get_object_or_404(
            InternshipProgram,
            id=program_id,
        )

        placement = InternshipPlacement.objects.create(
            student=student,
            program=program,
            school=student.school,
            department=program.department,
            company_name=program.company_name,
            project_title=(
                f"{program.title} - "
                f"Cohort "
                f"{program.academic_year}"
            ),
            academic_year=program.academic_year,
            start_date=(
                program.start_date
                or timezone.localdate()
            ),
            end_date=program.end_date,
            stipend_amount=program.stipend_amount,
            mentor_name=program.mentor_in_charge,
            mentor_email=program.mentor_contact,
            status=(
                InternshipPlacement.Status.SELECTED
            ),
            attendance_percentage=Decimal(
                "100.00"
            ),
            performance_grade=(
                InternshipPlacement
                .PerformanceGrade.PENDING
            ),
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    f"{student.student_name} "
                    f"assigned to "
                    f"{program.title}."
                ),
                "placement": _placement_to_dict(
                    placement
                ),
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


# =============================================================================
# KPI SUMMARY
# =============================================================================

def api_summary(request):

    academic_year = request.GET.get(
        "academic_year"
    )

    kpis = get_internship_kpis(
        academic_year
    )

    return JsonResponse(
        {
            "success": True,
            "kpis": kpis,
        }
    )


# =============================================================================
# CSV EXPORT
# =============================================================================

def api_export_csv(request):

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; '
        'filename="aequs_internship_records.csv"'
    )

    writer = csv.writer(response)

    writer.writerow(
        [
            "Placement ID",
            "Student Name",
            "Admission Number",
            "School / College",
            "Current Class",
            "Program Code",
            "Program Title",
            "Department",
            "Company / Division",
            "Project Title",
            "Academic Year",
            "Start Date",
            "End Date",
            "Monthly Stipend (INR)",
            "Mentor Name",
            "Mentor Email",
            "Status",
            "Attendance %",
            "Performance Grade",
            "Certificate Issued",
            "Certificate Number",
            "Supervisor Feedback",
        ]
    )

    placements = (
        InternshipPlacement.objects
        .select_related(
            "student",
            "school",
            "program",
        )
        .order_by("-start_date")
    )

    for p in placements:

        writer.writerow(
            [
                p.id,
                (
                    p.student.student_name
                    if p.student
                    else "N/A"
                ),
                (
                    p.student.admission_number
                    if p.student
                    else ""
                ),
                (
                    p.school.name
                    if p.school
                    else (
                        p.student.school.name
                        if (
                            p.student
                            and p.student.school
                        )
                        else "General"
                    )
                ),
                (
                    p.student.current_class
                    if p.student
                    else ""
                ),
                (
                    p.program.program_code
                    if p.program
                    else ""
                ),
                (
                    p.program.title
                    if p.program
                    else ""
                ),
                p.get_department_display(),
                p.company_name,
                p.project_title,
                p.academic_year,
                (
                    p.start_date.strftime("%Y-%m-%d")
                    if p.start_date
                    else ""
                ),
                (
                    p.end_date.strftime("%Y-%m-%d")
                    if p.end_date
                    else ""
                ),
                p.stipend_amount,
                p.mentor_name,
                p.mentor_email,
                p.get_status_display(),
                p.attendance_percentage,
                p.get_performance_grade_display(),
                (
                    "Yes"
                    if p.certificate_issued
                    else "No"
                ),
                p.certificate_number or "",
                p.evaluation_feedback or "",
            ]
        )

    return response


# =============================================================================
# ELIGIBILITY INTERNSHIP LIST
# =============================================================================

def internship_list(request):
    """
    List students who have been marked eligible
    for internships through the eligibility module.
    """

    records = (
        EligibilityRecord.objects
        .filter(
            benefit_type=BenefitType.INTERNSHIP,
            eligible=True,
        )
        .select_related("student")
        .order_by(
            "student__student_name"
        )
    )

    return render(
        request,
        "internships/list.html",
        {
            "records": records,
        },
    )
