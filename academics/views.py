import csv
import io
import json
import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .forms import AcademicRecordForm
from .models import AcademicRecord, CourseMaster
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

# ============================================================================
# JSON API - COURSE MASTER
# ============================================================================

def api_course_master(request):

    courses = (
        CourseMaster.objects
        .filter(is_active=True)
        .order_by(
            "category",
            "display_order",
            "name",
        )
    )

    data = [
        {
            "id": course.id,
            "name": course.name,
            "category": course.category,
            "category_label": course.get_category_display(),
            "display_order": course.display_order,
        }
        for course in courses
    ]

    return JsonResponse(
        {
            "success": True,
            "courses": data,
            "count": len(data),
        }
    )
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

def _normalize_academic_header(name):
    if not name:
        return ""
    cleaned = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    alias_map = {
        "admission_no": "admission_number",
        "adm_no": "admission_number",
        "admission_num": "admission_number",
        "adm_number": "admission_number",
        "student_name": "student_name",
        "name": "student_name",
        "full_name": "student_name",
        "student": "student_name",
        "year": "academic_year",
        "academic_year": "academic_year",
        "year_or_date": "academic_year",
        "class": "class_or_course",
        "grade": "class_or_course",
        "current_class": "class_or_course",
        "class_or_course": "class_or_course",
        "course": "class_or_course",
        "marks": "marks_obtained",
        "marks_obtained": "marks_obtained",
        "obtained_marks": "marks_obtained",
        "total_marks": "total_marks",
        "max_marks": "total_marks",
        "out_of": "total_marks",
        "percentage": "percentage",
        "percent": "percentage",
        "pct": "percentage",
        "status": "promotion_status",
        "promotion_status": "promotion_status",
        "result": "promotion_status",
        "previous_class": "previous_class",
        "prev_class": "previous_class",
        "transfer_school": "transfer_school",
        "remarks": "remarks",
    }
    return alias_map.get(cleaned, cleaned)


def _normalize_academic_year(year_str):
    """
    Normalize academic year representations (e.g., '2025-2026', '2025/2026', '2025-26')
    to standard 'YYYY-YY' format like '2025-26'.
    """
    if not year_str:
        return ""
    val = str(year_str).strip()
    m = re.match(r"^(\d{4})[-/](\d{2,4})$", val)
    if m:
        y1, y2 = m.group(1), m.group(2)
        if len(y2) == 4:
            y2 = y2[-2:]
        return f"{y1}-{y2}"
    return val


def academic_bulk_upload(request):
    """
    Bulk upload academic records from CSV or Excel (.xlsx).
    """

    if request.method == "GET":
        if request.GET.get("download") == "template":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="academic_bulk_upload_template.csv"'
            writer = csv.writer(response)
            writer.writerow([
                "Student Name",
                "Academic Year",
                "Class",
                "Percentage",
                "Rank",
                "Promotion Status",
            ])
            writer.writerow([
                "Kavish Goel",
                "2025-26",
                "10",
                "92.5",
                "1",
                "Promoted",
            ])
            writer.writerow([
                "Rhea Kapoor",
                "2025-26",
                "10",
                "88.0",
                "2",
                "Promoted",
            ])
            return response

        return render(
            request,
            "academics/bulk_upload.html",
        )

    uploaded_file = (
        request.FILES.get("academic_file")
        or request.FILES.get("csv_file")
        or request.FILES.get("file")
    )

    if not uploaded_file:
        messages.error(request, "Please select a CSV or Excel file to upload.")
        return redirect("academics:bulk_upload")

    filename = uploaded_file.name.lower()
    if not (filename.endswith(".csv") or filename.endswith(".xlsx")):
        messages.error(request, "Only CSV (.csv) and Excel (.xlsx) files are supported.")
        return redirect("academics:bulk_upload")

    try:
        rows_data = []

        if filename.endswith(".csv"):
            raw_data = uploaded_file.read()
            text = raw_data.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames:
                messages.error(request, "The CSV file is empty.")
                return redirect("academics:bulk_upload")

            for row in reader:
                normalized_row = {}
                for original_key, val in row.items():
                    norm_key = _normalize_academic_header(original_key)
                    if norm_key:
                        normalized_row[norm_key] = val
                rows_data.append(normalized_row)
        else:
            import openpyxl
            wb = openpyxl.load_workbook(uploaded_file, data_only=True)
            sheet = wb.active
            all_rows = list(sheet.iter_rows(values_only=True))
            if not all_rows or len(all_rows) < 2:
                messages.error(request, "The Excel file is empty.")
                return redirect("academics:bulk_upload")

            headers = [_normalize_academic_header(h) for h in all_rows[0]]
            for row_vals in all_rows[1:]:
                if not any(row_vals):
                    continue
                row_dict = {}
                for idx, val in enumerate(row_vals):
                    if idx < len(headers) and headers[idx]:
                        row_dict[headers[idx]] = str(val) if val is not None else ""
                rows_data.append(row_dict)

        if not rows_data:
            messages.error(request, "No rows found in the uploaded file.")
            return redirect("academics:bulk_upload")

        created_count = 0
        updated_count = 0
        errors = []

        with transaction.atomic():
            for row_number, row in enumerate(rows_data, start=2):
                try:
                    admission_number = str(row.get("admission_number") or "").strip()
                    student_name = str(row.get("student_name") or "").strip()
                    raw_academic_year = str(row.get("academic_year") or "2025-26").strip()
                    academic_year = _normalize_academic_year(raw_academic_year) or "2025-26"
                    class_or_course = str(row.get("class_or_course") or "").strip()

                    # Find student by student_name or admission_number
                    student = None
                    if student_name:
                        student = Student.objects.select_related("school").filter(student_name__iexact=student_name).first()
                    if not student and admission_number:
                        student = Student.objects.select_related("school").filter(admission_number__iexact=admission_number).first()
                    if not student and student_name:
                        student = Student.objects.select_related("school").filter(student_name__icontains=student_name).first()

                    if not student:
                        ident = student_name or admission_number or f"Row {row_number}"
                        raise ValueError(f"No student found for '{ident}'. Please ensure student is registered.")

                    if not class_or_course:
                        class_or_course = student.current_class or "General"

                    def clean_decimal(field_name):
                        val = str(row.get(field_name) or "").strip()
                        if not val or val == "-":
                            return None
                        try:
                            return Decimal(val)
                        except (InvalidOperation, ValueError):
                            raise ValueError(f"Invalid {field_name}: '{val}'.")

                    marks_obtained = clean_decimal("marks_obtained")
                    total_marks = clean_decimal("total_marks")
                    percentage = clean_decimal("percentage")

                    rank_int = None
                    rank_str = str(row.get("rank") or "").strip()
                    if rank_str and rank_str != "-":
                        try:
                            rank_int = int(Decimal(rank_str))
                        except Exception:
                            pass

                    promotion_status = str(row.get("promotion_status") or "Promoted").strip()
                    previous_class = str(row.get("previous_class") or "").strip()
                    transfer_school = str(row.get("transfer_school") or "").strip()
                    remarks = str(row.get("remarks") or "").strip()

                    # Find existing AcademicRecord to update/overwrite, or create new
                    candidate_years = list(dict.fromkeys([
                        academic_year,
                        raw_academic_year,
                        "2025-26",
                        "2025-2026",
                    ]))
                    record = (
                        AcademicRecord.objects.filter(
                            student=student,
                            academic_year=academic_year,
                            class_or_course=class_or_course,
                        ).first()
                        or AcademicRecord.objects.filter(
                            student=student,
                            academic_year__in=candidate_years,
                            class_or_course=class_or_course,
                        ).first()
                        or AcademicRecord.objects.filter(
                            student=student,
                            academic_year__in=candidate_years,
                        ).first()
                        or AcademicRecord.objects.filter(
                            student=student,
                            marks_obtained__isnull=True,
                            percentage__isnull=True,
                        ).first()
                        or AcademicRecord.objects.filter(
                            student=student,
                        ).first()
                    )

                    if record:
                        record.academic_year = academic_year
                        record.class_or_course = class_or_course
                        if marks_obtained is not None:
                            record.marks_obtained = marks_obtained
                        if total_marks is not None:
                            record.total_marks = total_marks
                        if marks_obtained is not None and total_marks is not None:
                            record.percentage = None
                        elif percentage is not None:
                            record.percentage = percentage
                        if rank_int is not None:
                            record.rank = rank_int
                        if previous_class:
                            record.previous_class = previous_class
                        if promotion_status:
                            record.promotion_status = promotion_status
                        if transfer_school:
                            record.transfer_school = transfer_school
                        if remarks:
                            record.remarks = remarks
                        record.save()
                        # Clean up any leftover empty duplicate records for this student
                        AcademicRecord.objects.filter(
                            student=student,
                            marks_obtained__isnull=True,
                            percentage__isnull=True,
                        ).exclude(id=record.id).delete()
                        updated_count += 1
                    else:
                        record = AcademicRecord(
                            student=student,
                            academic_year=academic_year,
                            class_or_course=class_or_course,
                            marks_obtained=marks_obtained,
                            total_marks=total_marks,
                            promotion_status=promotion_status,
                            transfer_school=transfer_school,
                            remarks=remarks,
                        )
                        if marks_obtained is None or total_marks is None:
                            record.percentage = percentage
                        if rank_int is not None:
                            record.rank = rank_int
                        if previous_class:
                            record.previous_class = previous_class
                        record.save()
                        # Clean up any leftover empty duplicate records for this student
                        AcademicRecord.objects.filter(
                            student=student,
                            marks_obtained__isnull=True,
                            percentage__isnull=True,
                        ).exclude(id=record.id).delete()
                        created_count += 1

                except Exception as exc:
                    errors.append(f"Row {row_number}: {exc}")

            if errors:
                error_msg = "Upload failed. The following rows contain errors:\n\n" + "\n".join(errors)
                raise ValueError(error_msg)

        messages.success(
            request,
            f"Academic bulk upload completed successfully! Created: {created_count}, Updated: {updated_count} record(s)."
        )
        return redirect("academics:portal")

    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception as exc:
        messages.error(request, f"Bulk upload failed: {exc}")

    return redirect("academics:bulk_upload")

