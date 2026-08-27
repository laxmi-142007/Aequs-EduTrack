import csv
import io
import random
from datetime import datetime

import openpyxl

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Student
from .forms import StudentForm
from schools.models import School
from academics.models import AcademicRecord


def _normalize_header_name(name):
    if not name:
        return ""
    cleaned = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    alias_map = {
        "admission_no": "admission_number",
        "adm_no": "admission_number",
        "admission_num": "admission_number",
        "student_name": "student_name",
        "name": "student_name",
        "full_name": "student_name",
        "class": "current_class",
        "grade": "current_class",
        "current_class": "current_class",
        "school_name": "school",
        "school": "school",
        "udise": "school",
        "udise_code": "school",
        "father_name": "parent_name",
        "parent_name": "parent_name",
        "guardian_name": "parent_name",
        "parent": "parent_name",
        "dob": "date_of_birth",
        "date_of_birth": "date_of_birth",
        "sex": "gender",
        "gender": "gender",
        "admission_date": "admission_date",
        "date_of_admission": "admission_date",
        "doj": "admission_date",
        "date_of_joining": "admission_date",
        "admission_dt": "admission_date",
    }
    return alias_map.get(cleaned, cleaned)


def student_list(request):
    queryset = (
        Student.objects
        .select_related("school")
        .all()
        .order_by("-id")
    )

    # ---------------------------------------------------------
    # FILTER PARAMETERS
    # ---------------------------------------------------------
    search_query = request.GET.get("q", "").strip()
    school_id = request.GET.get("school", "").strip()
    class_filter = request.GET.get("class", "").strip()
    gender_filter = request.GET.get("gender", "").strip()
    status_filter = request.GET.get("status", "").strip()

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------
    if search_query:
        queryset = queryset.filter(
            Q(student_name__icontains=search_query)
            | Q(admission_number__icontains=search_query)
            | Q(roll_number__icontains=search_query)
        )

    # ---------------------------------------------------------
    # SCHOOL FILTER
    # ---------------------------------------------------------
    if school_id:
        queryset = queryset.filter(
            school_id=school_id
        )

    # ---------------------------------------------------------
    # CLASS FILTER
    # ---------------------------------------------------------
    if class_filter:
        queryset = queryset.filter(
            current_class=class_filter
        )

    # ---------------------------------------------------------
    # GENDER FILTER
    # ---------------------------------------------------------
    if gender_filter:
        queryset = queryset.filter(
            gender=gender_filter
        )

    # ---------------------------------------------------------
    # STATUS FILTER
    # ---------------------------------------------------------
    if status_filter:
        queryset = queryset.filter(
            status=status_filter
        )

    # ---------------------------------------------------------
    # DISTINCT CLASSES
    # ---------------------------------------------------------
    distinct_classes = sorted(
        list(
            filter(
                None,
                Student.objects
                .values_list(
                    "current_class",
                    flat=True
                )
                .distinct()
            )
        )
    )

    # ---------------------------------------------------------
    # SCHOOLS
    # ---------------------------------------------------------
    schools = (
        School.objects
        .all()
        .order_by("name")
    )

    # ---------------------------------------------------------
    # COUNTS
    # ---------------------------------------------------------
    total_count = Student.objects.count()

    filtered_count = queryset.count()

    active_count = Student.objects.filter(
        status=Student.Status.ACTIVE
    ).count()

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------
    return render(
        request,
        "students/student_list.html",
        {
            "students": queryset,
            "schools": schools,
            "distinct_classes": distinct_classes,

            "search_query": search_query,
            "selected_school": school_id,
            "selected_class": class_filter,
            "selected_gender": gender_filter,
            "selected_status": status_filter,

            "gender_choices": Student.Gender.choices,
            "status_choices": Student.Status.choices,

            "total_count": total_count,
            "filtered_count": filtered_count,
            "active_count": active_count,
        },
    )


# =============================================================
# ADD STUDENT
# =============================================================

def add_student(request):

    if request.method == "POST":

        form = StudentForm(request.POST)

        if form.is_valid():

            student = form.save()

            try:
                from schools.views import _ensure_default_grades
                if student.school:
                    _ensure_default_grades(student.school)
            except Exception:
                pass

            messages.success(
                request,
                f"Student '{student.student_name}' added successfully."
            )

            return redirect(
                "students:list"
            )

    else:

        form = StudentForm()

    return render(
        request,
        "students/student_form.html",
        {
            "form": form,

            "is_edit": False,
        },
    )


# =============================================================
# BULK UPLOAD STUDENTS
# =============================================================

def bulk_upload_students(request):

    if request.method != "POST":

        return render(
            request,
            "students/bulk_upload.html",
        )

    uploaded_file = (
        request.FILES.get("student_file")
        or request.FILES.get("csv_file")
        or request.FILES.get("file")
    )

    if not uploaded_file:

        messages.error(
            request,
            "Please select a file to upload."
        )

        return redirect(
            "students:bulk_upload"
        )

    file_name = uploaded_file.name.lower()

    if not file_name.endswith((".csv", ".xlsx")):

        messages.error(
            request,
            "Only CSV and Excel (.xlsx) files are supported."
        )

        return redirect(
            "students:bulk_upload"
        )

    try:

        if file_name.endswith(".csv"):

            decoded_file = uploaded_file.read().decode(
                "utf-8-sig"
            )

            csv_file = io.StringIO(
                decoded_file
            )

            reader = csv.DictReader(
                csv_file
            )

            if not reader.fieldnames:

                messages.error(
                    request,
                    "The CSV file is empty."
                )

                return redirect(
                    "students:bulk_upload"
                )

            reader.fieldnames = [
                _normalize_header_name(field)
                for field in reader.fieldnames
            ]

            rows = list(reader)
            available_columns = set(reader.fieldnames)

        else:

            workbook = openpyxl.load_workbook(
                uploaded_file,
                read_only=True,
                data_only=True,
            )

            worksheet = workbook.active

            excel_rows = list(
                worksheet.iter_rows(
                    values_only=True
                )
            )

            workbook.close()

            if not excel_rows:

                messages.error(
                    request,
                    "The Excel file is empty."
                )

                return redirect(
                    "students:bulk_upload"
                )

            headers = [
                _normalize_header_name(cell) if cell is not None else ""
                for cell in excel_rows[0]
            ]

            available_columns = set(
                headers
            )

            rows = []

            for excel_row in excel_rows[1:]:

                if not any(
                    cell is not None
                    and str(cell).strip() != ""
                    for cell in excel_row
                ):
                    continue

                row_data = {}

                for index, header in enumerate(
                    headers
                ):

                    if not header:
                        continue

                    value = (
                        excel_row[index]
                        if index < len(excel_row)
                        else ""
                    )

                    row_data[header] = (
                        ""
                        if value is None
                        else value
                    )

                rows.append(
                    row_data
                )

        required_columns = {
            "student_name",
        }

        missing_columns = (
            required_columns
            - available_columns
        )

        if missing_columns:

            messages.error(
                request,
                "Missing required column: 'student_name' (or 'Student Name')."
            )

            return redirect(
                "students:bulk_upload"
            )

        if not rows:

            messages.error(
                request,
                "The file contains no student records."
            )

            return redirect(
                "students:bulk_upload"
            )

        errors = []
        prepared_students = []
        uploaded_admission_numbers = set()

        target_school_id = request.GET.get("school") or request.POST.get("school_id")
        default_target_school = None
        if target_school_id:
            default_target_school = School.objects.filter(id=target_school_id).first()
        if not default_target_school and School.objects.count() == 1:
            default_target_school = School.objects.first()

        for row_number, row in enumerate(
            rows,
            start=2
        ):

            admission_number = str(
                row.get("admission_number") or ""
            ).strip()

            student_name = str(
                row.get("student_name") or ""
            ).strip()

            gender = str(
                row.get("gender") or ""
            ).strip().upper()

            school_name = str(
                row.get("school") or ""
            ).strip()

            current_class = str(
                row.get("current_class") or ""
            ).strip() or "General"

            parent_name = str(
                row.get("parent_name") or ""
            ).strip() or "Guardian"

            if not student_name:
                errors.append(
                    f"Row {row_number}: student_name is required."
                )

            if not gender:
                gender = "MALE"
            elif gender not in dict(Student.Gender.choices):
                if "FEMALE" in gender or "GIRL" in gender or "F" == gender:
                    gender = "FEMALE"
                elif "OTHER" in gender:
                    gender = "OTHER"
                else:
                    gender = "MALE"

            if not admission_number:
                while True:
                    candidate = f"ADM{random.randint(100000, 999999)}"
                    if (
                        candidate not in uploaded_admission_numbers
                        and not Student.objects.filter(admission_number=candidate).exists()
                    ):
                        admission_number = candidate
                        uploaded_admission_numbers.add(candidate)
                        break

            school = None
            if school_name:
                school = (
                    School.objects.filter(name__iexact=school_name).first()
                    or School.objects.filter(udise_code__iexact=school_name).first()
                    or School.objects.filter(name__icontains=school_name).first()
                )
            if not school and default_target_school:
                school = default_target_school
            if not school:
                school = School.objects.first()

            if admission_number:
                if admission_number in uploaded_admission_numbers:
                    errors.append(
                        f"Row {row_number}: admission number '{admission_number}' is duplicated in the uploaded file."
                    )
                else:
                    uploaded_admission_numbers.add(admission_number)

                if Student.objects.filter(admission_number=admission_number).exists():
                    errors.append(
                        f"Row {row_number}: admission number '{admission_number}' already exists in database."
                    )

            date_of_birth = None
            dob_value = row.get("date_of_birth", "")
            if dob_value:
                if isinstance(dob_value, datetime):
                    date_of_birth = dob_value.date()
                elif hasattr(dob_value, "date"):
                    date_of_birth = dob_value.date()
                else:
                    dob_str = str(dob_value).strip()
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                        try:
                            date_of_birth = datetime.strptime(dob_str, fmt).date()
                            break
                        except ValueError:
                            pass
            admission_date = None
            adm_date_val = row.get("admission_date", "")
            if adm_date_val:
                if isinstance(adm_date_val, datetime):
                    admission_date = adm_date_val.date()
                elif hasattr(adm_date_val, "date"):
                    admission_date = adm_date_val.date()
                else:
                    adm_date_str = str(adm_date_val).strip()
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                        try:
                            admission_date = datetime.strptime(adm_date_str, fmt).date()
                            break
                        except ValueError:
                            pass

            # -------------------------------------------------
            # STATUS
            # -------------------------------------------------

            status = str(
                row.get(
                    "status"
                )
                or Student.Status.ACTIVE
            ).strip().upper()

            if status not in dict(
                Student.Status.choices
            ):

                errors.append(
                    f"Row {row_number}: "
                    f"invalid status '{status}'. "
                    "Use ACTIVE, TRANSFERRED, "
                    "PASSED_OUT or INACTIVE."
                )

            # -------------------------------------------------
            # PREPARE STUDENT
            # -------------------------------------------------

            prepared_students.append(
                {
                    "row_number": row_number,

                    "admission_number":
                        admission_number,

                    "student_name":
                        student_name,

                    "date_of_birth":
                        date_of_birth,

                    "gender":
                        gender,

                    "school":
                        school,

                    "current_class":
                        current_class,

                    "section":
                        str(
                            row.get(
                                "section"
                            )
                            or ""
                        ).strip(),

                    "roll_number":
                        str(
                            row.get(
                                "roll_number"
                            )
                            or ""
                        ).strip(),

                    "parent_name":
                        parent_name,

                    "parent_phone":
                        str(
                            row.get(
                                "parent_phone"
                            )
                            or ""
                        ).strip(),

                    "parent_email":
                        str(
                            row.get(
                                "parent_email"
                            )
                            or ""
                        ).strip(),

                    "relationship_to_student":
                        str(
                            row.get(
                                "relationship_to_student"
                            )
                            or "Parent"
                        ).strip(),

                    "student_phone":
                        str(
                            row.get(
                                "student_phone"
                            )
                            or ""
                        ).strip(),

                    "email":
                        str(
                            row.get(
                                "email"
                            )
                            or ""
                        ).strip(),

                    "address":
                        str(
                            row.get(
                                "address"
                            )
                            or ""
                        ).strip(),

                    "status":
                        status,

                    "admission_date":
                        admission_date,
                }
            )

        # =====================================================
        # VALIDATION FAILED
        # =====================================================

        if errors:

            return render(
                request,
                "students/bulk_upload.html",
                {
                    "errors": errors,
                    "upload_failed": True,
                },
            )

        # =====================================================
        # CREATE STUDENTS
        # =====================================================

        created_count = 0

        with transaction.atomic():

            for data in prepared_students:

                data.pop(
                    "row_number",
                    None
                )

                student = Student.objects.create(
                    **data
                )

                # Automatically create academic record
                AcademicRecord.objects.get_or_create(
                    student=student,
                    academic_year="2025-26",
                    class_or_course=student.current_class,
                )

                created_count += 1

        # =====================================================
        # SUCCESS
        # =====================================================

        messages.success(
            request,
            f"Successfully uploaded "
            f"{created_count} student(s)."
        )

        return redirect(
            "students:list"
        )

    # =========================================================
    # CSV ENCODING ERROR
    # =========================================================

    except UnicodeDecodeError:

        messages.error(
            request,
            "Could not read the CSV file. "
            "Please save it as UTF-8 CSV."
        )

        return redirect(
            "students:bulk_upload"
        )

    # =========================================================
    # GENERAL ERROR
    # =========================================================

    except Exception as exc:

        messages.error(
            request,
            f"Bulk upload failed: {exc}"
        )

        return redirect(
            "students:bulk_upload"
        )


@require_http_methods(["POST"])
def clear_all_students(request):
    """Clear/delete all student records and recalculate school strengths."""
    try:
        from eligibility.models import EligibilityRecord
        from distributions.models import Distribution
        from academics.models import AcademicRecord
        from inventory.models import LaptopAssignment
        from schools.models import GradeStrength, School

        with transaction.atomic():
            LaptopAssignment.objects.all().delete()
            Distribution.objects.all().delete()
            EligibilityRecord.objects.all().delete()
            AcademicRecord.objects.all().delete()
            deleted_count, _ = Student.objects.all().delete()

            # Recalculate school student strength and grade strengths for all schools
            for school in School.objects.all():
                school.grade_strengths.all().delete()
                if school.student_strength != 0:
                    school.student_strength = 0
                    school.save(update_fields=["student_strength"])

        try:
            from reports.models import log_activity
            log_activity(request, f"Cleared all students from database ({deleted_count} students deleted)", category="STUDENT")
        except Exception:
            pass

        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json":
            return JsonResponse({
                "success": True,
                "message": f"Successfully deleted {deleted_count} student record(s)."
            })

        messages.success(
            request,
            f"Successfully deleted {deleted_count} student record(s)."
        )
        return redirect("students:list")

    except Exception as e:
        import traceback
        traceback.print_exc()
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json":
            return JsonResponse({"success": False, "error": str(e)}, status=500)
        messages.error(request, f"Failed to clear students: {e}")
        return redirect("students:list")