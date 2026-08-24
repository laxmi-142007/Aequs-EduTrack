import csv
import io
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .forms import AcademicRecordForm
from .models import AcademicRecord
from students.models import Student
from schools.models import School


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _record_to_dict(rec):
    return {
        "id": rec.id,
        "student_id": rec.student.id if rec.student else None,
        "student_name": (
            rec.student.student_name
            if rec.student
            else "Unknown"
        ),
        "admission_number": (
            rec.student.admission_number
            if rec.student
            else ""
        ),
        "school_name": (
            rec.student.school.name
            if rec.student and rec.student.school
            else "General"
        ),
        "academic_year": rec.academic_year,
        "class_or_course": rec.class_or_course,
        "marks_obtained": (
            float(rec.marks_obtained)
            if rec.marks_obtained is not None
            else None
        ),
        "total_marks": (
            float(rec.total_marks)
            if rec.total_marks is not None
            else None
        ),
        "percentage": (
            float(rec.percentage)
            if rec.percentage is not None
            else None
        ),
        "rank": rec.rank,
        "previous_class": rec.previous_class or "",
        "promotion_status": rec.promotion_status or "Promoted",
        "transfer_school": rec.transfer_school or "",
        "remarks": rec.remarks or "",
        "created_at": (
            rec.created_at.strftime("%Y-%m-%d")
            if rec.created_at
            else ""
        ),
    }


def _ensure_initial_data():
    """
    Create a small set of sample academic data only when
    there are no academic records.
    """

    if AcademicRecord.objects.exists():
        return

    school = School.objects.first()

    if not school:
        school = School.objects.create(
            name="Govt. Model High School",
            udise_code="29010200301",
            district="Bangalore Urban",
            village="Jayanagar",
        )

    sample_data = [
        {
            "name": "Aarav Sharma",
            "adm": "ADM-2023-001",
            "year": "2023-2024",
            "class": "Class 5",
            "pct": Decimal("92.50"),
            "status": "Promoted",
        },
        {
            "name": "Diya Patel",
            "adm": "ADM-2023-002",
            "year": "2023-2024",
            "class": "Class 5",
            "pct": Decimal("88.00"),
            "status": "Promoted",
        },
        {
            "name": "Rohan Gupta",
            "adm": "ADM-2023-003",
            "year": "2023-2024",
            "class": "Class 5",
            "pct": Decimal("45.00"),
            "status": "Conditional",
        },
        {
            "name": "Sanya Iyer",
            "adm": "ADM-2023-004",
            "year": "2023-2024",
            "class": "Class 5",
            "pct": Decimal("32.00"),
            "status": "Not Promoted",
        },
    ]

    for item in sample_data:
        student, _ = Student.objects.get_or_create(
            admission_number=item["adm"],
            defaults={
                "student_name": item["name"],
                "school": school,
                "current_class": item["class"],
                "parent_name": "Parent of " + item["name"],
            },
        )

        AcademicRecord.objects.create(
            student=student,
            academic_year=item["year"],
            class_or_course=item["class"],
            percentage=item["pct"],
            promotion_status=item["status"],
        )


# ============================================================================
# MAIN ACADEMIC PORTAL
# ============================================================================

@ensure_csrf_cookie
def academic_portal(request):
    """
    Main Academic Record Management Portal.
    """

    _ensure_initial_data()

    records = (
        AcademicRecord.objects
        .select_related("student", "student__school")
        .order_by(
            "-academic_year",
            "rank",
            "student__student_name",
        )
    )

    students = (
        Student.objects
        .select_related("school")
        .order_by("student_name")
    )

    total_records = records.count()

    promoted_count = records.filter(
        promotion_status__iexact="Promoted"
    ).count()

    conditional_count = records.filter(
        promotion_status__iexact="Conditional"
    ).count()

    not_promoted_count = records.filter(
        promotion_status__icontains="Not"
    ).count()

    context = {
        "records": records,
        "students": students,
        "total_records": total_records,
        "promoted_count": promoted_count,
        "conditional_count": conditional_count,
        "not_promoted_count": not_promoted_count,
        "user_authenticated": request.user.is_authenticated,
        "username": (
            request.user.username
            if request.user.is_authenticated
            else "Admin"
        ),
    }

    return render(
        request,
        "academics/portal.html",
        context,
    )


# ============================================================================
# ACADEMIC LIST
# ============================================================================

def academic_list(request):
    """
    Traditional academic list page.
    """

    records = (
        AcademicRecord.objects
        .select_related("student", "student__school")
        .all()
    )

    return render(
        request,
        "academics/academic_list.html",
        {
            "records": records,
        },
    )


# ============================================================================
# CREATE / UPDATE / DELETE
# ============================================================================

def academic_create(request):

    if request.method == "POST":

        form = AcademicRecordForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Academic record added successfully.",
            )
            return redirect("academics:list")

    else:
        form = AcademicRecordForm()

    return render(
        request,
        "academics/academic_form.html",
        {
            "form": form,
        },
    )


def academic_update(request, pk):

    record = get_object_or_404(
        AcademicRecord,
        pk=pk,
    )

    if request.method == "POST":

        form = AcademicRecordForm(
            request.POST,
            instance=record,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Academic record updated successfully.",
            )

            return redirect("academics:list")

    else:
        form = AcademicRecordForm(
            instance=record,
        )

    return render(
        request,
        "academics/academic_form.html",
        {
            "form": form,
            "record": record,
        },
    )


def academic_delete(request, pk):

    record = get_object_or_404(
        AcademicRecord,
        pk=pk,
    )

    if request.method == "POST":

        record.delete()

        messages.success(
            request,
            "Academic record deleted successfully.",
        )

        return redirect("academics:list")

    return render(
        request,
        "academics/academic_confirm_delete.html",
        {
            "record": record,
        },
    )


# ============================================================================
# JSON API - LIST RECORDS
# ============================================================================

def api_academic_records(request):

    records = (
        AcademicRecord.objects
        .select_related("student", "student__school")
        .all()
    )

    year = request.GET.get("year")
    student_class = request.GET.get("class")
    status = request.GET.get("status")
    search = request.GET.get("search")

    if year:
        records = records.filter(
            academic_year=year
        )

    if student_class:
        records = records.filter(
            class_or_course=student_class
        )

    if status:
        records = records.filter(
            promotion_status__iexact=status
        )

    if search:
        records = records.filter(
            student__student_name__icontains=search
        )

    data = [
        _record_to_dict(record)
        for record in records
    ]

    return JsonResponse(
        {
            "success": True,
            "records": data,
            "count": len(data),
        }
    )


# ============================================================================
# JSON API - CREATE
# ============================================================================

@require_http_methods(["POST"])
def api_create_academic_record(request):

    try:

        if request.content_type == "application/json":
            data = json.loads(
                request.body.decode("utf-8")
            )
        else:
            data = request.POST

        student_name = (
            data.get("studentName", "")
            or ""
        ).strip()

        student_id = data.get("studentId")

        academic_year = (
            data.get("academicYear", "")
            or ""
        ).strip()

        student_class = (
            data.get("studentClass")
            or data.get("class_or_course", "")
            or ""
        ).strip()

        percentage = data.get("percentage")

        marks_obtained = data.get("marksObtained")
        total_marks = data.get("totalMarks")

        rank = data.get("rank")

        promotion_status = (
            data.get("promotionDetails")
            or data.get(
                "promotion_status",
                "Promoted",
            )
            or "Promoted"
        ).strip()

        school_transfer = (
            data.get("schoolTransfer", "No")
            or "No"
        )

        transfer_details = (
            data.get("transferDetails")
            or data.get("transfer_school", "")
            or ""
        ).strip()

        remarks = (
            data.get("remarks", "")
            or ""
        ).strip()

        if not student_name and not student_id:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Student Name is required.",
                },
                status=400,
            )

        if not academic_year:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Academic Year is required.",
                },
                status=400,
            )

        if not student_class:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Class is required.",
                },
                status=400,
            )

        # Resolve student.
        student = None

        if student_id:
            student = (
                Student.objects
                .filter(id=student_id)
                .first()
            )

        if not student and student_name:
            student = (
                Student.objects
                .filter(
                    student_name__iexact=student_name
                )
                .first()
            )

        if not student and student_name:

            school = School.objects.first()

            if not school:
                school = School.objects.create(
                    name="Govt. Model School",
                    udise_code="29010200001",
                    district="General",
                )

            import random

            adm_no = (
                f"ADM-{random.randint(1000, 9999)}"
            )

            student = Student.objects.create(
                student_name=student_name,
                admission_number=adm_no,
                school=school,
                current_class=student_class,
                parent_name=(
                    "Parent of " + student_name
                ),
            )

        def decimal_or_none(value):

            if value in (None, ""):
                return None

            return Decimal(str(value))

        marks_value = decimal_or_none(
            marks_obtained
        )

        total_value = decimal_or_none(
            total_marks
        )

        percentage_value = decimal_or_none(
            percentage
        )

        rank_value = None

        if rank not in (None, ""):
            rank_value = int(rank)

        transfer_value = (
            transfer_details
            if (
                school_transfer == "Yes"
                or transfer_details
            )
            else ""
        )

        record = AcademicRecord.objects.create(
            student=student,
            academic_year=academic_year,
            class_or_course=student_class,
            marks_obtained=marks_value,
            total_marks=total_value,
            percentage=percentage_value,
            rank=rank_value,
            promotion_status=promotion_status,
            transfer_school=transfer_value,
            remarks=remarks,
        )

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Academic record for "
                    f"{student.student_name} "
                    "saved successfully!"
                ),
                "record": _record_to_dict(record),
            }
        )

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================================
# JSON API - UPDATE
# ============================================================================

@require_http_methods(["POST"])
def api_update_academic_record(
    request,
    record_id,
):

    try:

        record = get_object_or_404(
            AcademicRecord,
            id=record_id,
        )

        if request.content_type == "application/json":
            data = json.loads(
                request.body.decode("utf-8")
            )
        else:
            data = request.POST

        if "academicYear" in data:
            record.academic_year = (
                data["academicYear"] or ""
            ).strip()

        if "studentClass" in data:
            record.class_or_course = (
                data["studentClass"] or ""
            ).strip()

        if "marksObtained" in data:
            value = data["marksObtained"]

            record.marks_obtained = (
                Decimal(str(value))
                if value not in ("", None)
                else None
            )

        if "totalMarks" in data:
            value = data["totalMarks"]

            record.total_marks = (
                Decimal(str(value))
                if value not in ("", None)
                else None
            )

        if "percentage" in data:
            value = data["percentage"]

            record.percentage = (
                Decimal(str(value))
                if value not in ("", None)
                else None
            )

        if "rank" in data:

            value = data["rank"]

            record.rank = (
                int(value)
                if value not in ("", None)
                else None
            )

        if "promotionDetails" in data:

            record.promotion_status = (
                data["promotionDetails"]
                or ""
            ).strip()

        if "promotion_status" in data:

            record.promotion_status = (
                data["promotion_status"]
                or ""
            ).strip()

        if "transferDetails" in data:

            record.transfer_school = (
                data["transferDetails"]
                or ""
            ).strip()

        if "transfer_school" in data:

            record.transfer_school = (
                data["transfer_school"]
                or ""
            ).strip()

        if "remarks" in data:

            record.remarks = (
                data["remarks"]
                or ""
            ).strip()

        record.save()

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Academic record updated successfully!"
                ),
                "record": _record_to_dict(record),
            }
        )

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================================
# JSON API - DELETE
# ============================================================================

@require_http_methods(["POST"])
def api_delete_academic_record(
    request,
    record_id,
):

    try:

        record = get_object_or_404(
            AcademicRecord,
            id=record_id,
        )

        record.delete()

        return JsonResponse(
            {
                "success": True,
                "message": (
                    "Academic record deleted successfully."
                ),
            }
        )

    except Exception as exc:

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )


# ============================================================================
# JSON API - STUDENTS
# ============================================================================

def api_get_students(request):

    students = (
        Student.objects
        .select_related("school")
        .all()
        .order_by("student_name")
    )

    data = []

    for student in students:

        data.append(
            {
                "id": student.id,
                "name": student.student_name,
                "admission_number": (
                    student.admission_number
                ),
                "current_class": (
                    student.current_class
                ),
                "school": (
                    student.school.name
                    if student.school
                    else ""
                ),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "students": data,
        }
    )


# ============================================================================
# BULK UPLOAD
# ============================================================================

def academic_bulk_upload(request):
    """
    Bulk upload academic records from CSV.

    Required columns:
        admission_number
        academic_year
        class_or_course

    Optional columns:
        marks_obtained
        total_marks
        percentage
        previous_class
        promotion_status
        transfer_school
        remarks
    """

    # ------------------------------------------------------------------------
    # GET = display upload page / download template
    # ------------------------------------------------------------------------

    if request.method == "GET":

        if request.GET.get("download") == "template":

            response = HttpResponse(
                content_type="text/csv"
            )

            response[
                "Content-Disposition"
            ] = (
                'attachment; '
                'filename="academic_bulk_upload_template.csv"'
            )

            writer = csv.writer(response)

            writer.writerow(
                [
                    "admission_number",
                    "academic_year",
                    "class_or_course",
                    "marks_obtained",
                    "total_marks",
                    "percentage",
                    "previous_class",
                    "promotion_status",
                    "transfer_school",
                    "remarks",
                ]
            )

            writer.writerow(
                [
                    "ADM-2023-001",
                    "2025-2026",
                    "Class 6",
                    "450",
                    "500",
                    "",
                    "",
                    "Promoted",
                    "",
                    "",
                ]
            )

            return response

        return render(
            request,
            "academics/bulk_upload.html",
        )

    # ------------------------------------------------------------------------
    # POST = process uploaded CSV
    # ------------------------------------------------------------------------

    uploaded_file = request.FILES.get(
        "academic_file"
    )

    if not uploaded_file:

        messages.error(
            request,
            "Please select a CSV file.",
        )

        return redirect(
            "academics:bulk_upload"
        )

    if not uploaded_file.name.lower().endswith(
        ".csv"
    ):

        messages.error(
            request,
            "Only CSV files are supported.",
        )

        return redirect(
            "academics:bulk_upload"
        )

    try:

        raw_data = uploaded_file.read()

        text = raw_data.decode(
            "utf-8-sig"
        )

        reader = csv.DictReader(
            io.StringIO(text)
        )

        if not reader.fieldnames:

            messages.error(
                request,
                "The CSV file is empty.",
            )

            return redirect(
                "academics:bulk_upload"
            )

        # Normalize column names.
        reader.fieldnames = [
            field.strip().lower().replace(
                " ",
                "_",
            )
            if field
            else ""
            for field in reader.fieldnames
        ]

        required_columns = {
            "admission_number",
            "academic_year",
            "class_or_course",
        }

        missing = (
            required_columns
            - set(reader.fieldnames)
        )

        if missing:

            messages.error(
                request,
                "Missing required columns: "
                + ", ".join(
                    sorted(missing)
                ),
            )

            return redirect(
                "academics:bulk_upload"
            )

        created_count = 0
        updated_count = 0
        errors = []

        rows = list(reader)

        # --------------------------------------------------------------------
        # Validate/process entire file as one transaction.
        # --------------------------------------------------------------------

        with transaction.atomic():

            for row_number, row in enumerate(
                rows,
                start=2,
            ):

                try:

                    admission_number = (
                        row.get(
                            "admission_number"
                        )
                        or ""
                    ).strip()

                    academic_year = (
                        row.get(
                            "academic_year"
                        )
                        or ""
                    ).strip()

                    class_or_course = (
                        row.get(
                            "class_or_course"
                        )
                        or ""
                    ).strip()

                    if not admission_number:
                        raise ValueError(
                            "Admission number is required."
                        )

                    if not academic_year:
                        raise ValueError(
                            "Academic year is required."
                        )

                    if not class_or_course:
                        raise ValueError(
                            "Class/course is required."
                        )

                    # --------------------------------------------------------
                    # Find student.
                    # --------------------------------------------------------

                    student = (
                        Student.objects
                        .select_related("school")
                        .filter(
                            admission_number__iexact=(
                                admission_number
                            )
                        )
                        .first()
                    )

                    if not student:

                        raise ValueError(
                            "No student found with "
                            f"admission number "
                            f"'{admission_number}'."
                        )

                    # --------------------------------------------------------
                    # Decimal helper.
                    # --------------------------------------------------------

                    def clean_decimal(
                        field_name
                    ):

                        value = (
                            row.get(field_name)
                            or ""
                        ).strip()

                        if value == "":
                            return None

                        try:

                            return Decimal(
                                value
                            )

                        except (
                            InvalidOperation,
                            ValueError,
                        ):

                            raise ValueError(
                                f"Invalid "
                                f"{field_name}: "
                                f"'{value}'."
                            )

                    marks_obtained = (
                        clean_decimal(
                            "marks_obtained"
                        )
                    )

                    total_marks = (
                        clean_decimal(
                            "total_marks"
                        )
                    )

                    percentage = (
                        clean_decimal(
                            "percentage"
                        )
                    )

                    # --------------------------------------------------------
                    # Validate marks.
                    # --------------------------------------------------------

                    if marks_obtained is not None:

                        if marks_obtained < 0:
                            raise ValueError(
                                "Marks obtained "
                                "cannot be negative."
                            )

                    if total_marks is not None:

                        if total_marks <= 0:
                            raise ValueError(
                                "Total marks must "
                                "be greater than zero."
                            )

                    if (
                        marks_obtained is not None
                        and total_marks is not None
                        and marks_obtained > total_marks
                    ):

                        raise ValueError(
                            "Marks obtained cannot "
                            "be greater than total marks."
                        )

                    if percentage is not None:

                        if (
                            percentage < 0
                            or percentage > 100
                        ):

                            raise ValueError(
                                "Percentage must "
                                "be between 0 and 100."
                            )

                    # --------------------------------------------------------
                    # Rank is normally calculated by model.save().
                    # Do not force an uploaded rank because the model
                    # automatically recalculates ranks.
                    # --------------------------------------------------------

                    promotion_status = (
                        row.get(
                            "promotion_status"
                        )
                        or ""
                    ).strip()

                    previous_class = (
                        row.get(
                            "previous_class"
                        )
                        or ""
                    ).strip()

                    transfer_school = (
                        row.get(
                            "transfer_school"
                        )
                        or ""
                    ).strip()

                    remarks = (
                        row.get(
                            "remarks"
                        )
                        or ""
                    ).strip()

                    # --------------------------------------------------------
                    # Find existing record using the model's unique key.
                    # --------------------------------------------------------

                    record = (
                        AcademicRecord.objects
                        .filter(
                            student=student,
                            academic_year=academic_year,
                            class_or_course=class_or_course,
                        )
                        .first()
                    )

                    if record:

                        record.marks_obtained = (
                            marks_obtained
                        )

                        record.total_marks = (
                            total_marks
                        )

                        # If marks are supplied, the model will calculate
                        # percentage automatically.
                        #
                        # If marks are not supplied, preserve the uploaded
                        # percentage.
                        if (
                            marks_obtained is not None
                            and total_marks is not None
                        ):
                            record.percentage = None
                        elif percentage is not None:
                            record.percentage = percentage

                        if previous_class:
                            record.previous_class = (
                                previous_class
                            )

                        record.promotion_status = (
                            promotion_status
                        )

                        record.transfer_school = (
                            transfer_school
                        )

                        record.remarks = remarks

                        record.save()

                        updated_count += 1

                    else:

                        record = AcademicRecord(
                            student=student,
                            academic_year=academic_year,
                            class_or_course=class_or_course,
                            marks_obtained=(
                                marks_obtained
                            ),
                            total_marks=(
                                total_marks
                            ),
                            promotion_status=(
                                promotion_status
                            ),
                            transfer_school=(
                                transfer_school
                            ),
                            remarks=remarks,
                        )

                        if (
                            marks_obtained is None
                            or total_marks is None
                        ):
                            record.percentage = (
                                percentage
                            )

                        if previous_class:
                            record.previous_class = (
                                previous_class
                            )

                        record.save()

                        created_count += 1

                except Exception as exc:

                    errors.append(
                        f"Row {row_number}: {exc}"
                    )

            # ---------------------------------------------------------------
            # If any row fails, roll back the entire upload.
            # ---------------------------------------------------------------

            if errors:

                error_message = (
                    "Upload failed. No records were "
                    "saved because the following "
                    "rows contain errors:\n\n"
                    + "\n".join(errors)
                )

                raise ValueError(
                    error_message
                )

        messages.success(
            request,
            (
                "Upload completed successfully. "
                f"Created: {created_count}, "
                f"Updated: {updated_count}."
            ),
        )

    except UnicodeDecodeError:

        messages.error(
            request,
            (
                "The CSV file is not UTF-8 encoded. "
                "Please save the CSV as UTF-8 and "
                "upload again."
            ),
        )

    except ValueError as exc:

        messages.error(
            request,
            str(exc),
        )

    except Exception as exc:

        messages.error(
            request,
            f"Upload failed: {exc}",
        )

    return redirect(
        "academics:bulk_upload"
    )