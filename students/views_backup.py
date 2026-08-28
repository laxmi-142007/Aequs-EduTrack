import csv
import io
from datetime import datetime

import openpyxl

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect

from .models import Student
from .forms import StudentForm
from schools.models import School
from academics.models import AcademicRecord


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

            AcademicRecord.objects.get_or_create(
                student=student,
                academic_year="2025-26",
                class_or_course=student.current_class,
            )

            messages.success(
                request,
                f"Student '{student.student_name}' "
                "was added successfully."
            )

            return redirect(
                "students:list"
            )

    else:

        form = StudentForm()

    return render(
        request,
        "students/add_student.html",
        {
            "form": form
        },
    )


# =============================================================
# BULK UPLOAD STUDENTS
# =============================================================

def bulk_upload_students(request):

    # ---------------------------------------------------------
    # SHOW UPLOAD PAGE
    # ---------------------------------------------------------
    if request.method != "POST":

        return render(
            request,
            "students/bulk_upload.html",
        )

    # ---------------------------------------------------------
    # GET FILE
    # ---------------------------------------------------------
    uploaded_file = request.FILES.get(
        "csv_file"
    )

    if not uploaded_file:

        messages.error(
            request,
            "Please select a CSV or Excel (.xlsx) file."
        )

        return redirect(
            "students:bulk_upload"
        )

    file_name = uploaded_file.name.lower()

    # ---------------------------------------------------------
    # VALIDATE FILE TYPE
    # ---------------------------------------------------------
    if not (
        file_name.endswith(".csv")
        or file_name.endswith(".xlsx")
    ):

        messages.error(
            request,
            "Only CSV and Excel (.xlsx) files are supported."
        )

        return redirect(
            "students:bulk_upload"
        )

    try:

        # =====================================================
        # READ CSV
        # =====================================================

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

            # Normalize CSV column names
            reader.fieldnames = [
                str(field).strip().lower()
                if field
                else ""
                for field in reader.fieldnames
            ]

            rows = list(reader)

            available_columns = set(
                reader.fieldnames
            )

        # =====================================================
        # READ EXCEL
        # =====================================================

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

            # -------------------------------------------------
            # HEADER ROW
            # -------------------------------------------------

            headers = []

            for cell in excel_rows[0]:

                if cell is None:

                    headers.append("")

                else:

                    headers.append(
                        str(cell)
                        .strip()
                        .lower()
                    )

            available_columns = set(
                headers
            )

            # -------------------------------------------------
            # CONVERT EXCEL TO DICTIONARIES
            # -------------------------------------------------

            rows = []

            for excel_row in excel_rows[1:]:

                # Ignore completely empty rows
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
                        else None
                    )

                    row_data[header] = value

                rows.append(
                    row_data
                )

        # =====================================================
        # REQUIRED COLUMNS
        # =====================================================

        required_columns = {
            "admission_number",
            "student_name",
            "gender",
            "school",
            "current_class",
            "parent_name",
        }

        missing_columns = (
            required_columns
            - available_columns
        )

        if missing_columns:

            messages.error(
                request,
                "Missing columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

            return redirect(
                "students:bulk_upload"
            )

        # =====================================================
        # CHECK EMPTY RECORDS
        # =====================================================

        if not rows:

            messages.error(
                request,
                "The file contains no student records."
            )

            return redirect(
                "students:bulk_upload"
            )

        # =====================================================
        # VALIDATION
        # =====================================================

        errors = []

        prepared_students = []

        # Track admission numbers inside uploaded file
        uploaded_admission_numbers = set()

        # =====================================================
        # PROCESS EVERY ROW
        # =====================================================

        for row_number, row in enumerate(
            rows,
            start=2
        ):

            # -------------------------------------------------
            # REQUIRED VALUES
            # -------------------------------------------------

            admission_number = str(
                row.get(
                    "admission_number"
                )
                or ""
            ).strip()

            student_name = str(
                row.get(
                    "student_name"
                )
                or ""
            ).strip()

            gender = str(
                row.get(
                    "gender"
                )
                or ""
            ).strip().upper()

            school_name = str(
                row.get(
                    "school"
                )
                or ""
            ).strip()

            current_class = str(
                row.get(
                    "current_class"
                )
                or ""
            ).strip()

            parent_name = str(
                row.get(
                    "parent_name"
                )
                or ""
            ).strip()

            # -------------------------------------------------
            # REQUIRED FIELD VALIDATION
            # -------------------------------------------------

            if not admission_number:

                errors.append(
                    f"Row {row_number}: "
                    "admission_number is required."
                )

            if not student_name:

                errors.append(
                    f"Row {row_number}: "
                    "student_name is required."
                )

            if not gender:

                errors.append(
                    f"Row {row_number}: "
                    "gender is required."
                )

            elif gender not in dict(
                Student.Gender.choices
            ):

                errors.append(
                    f"Row {row_number}: "
                    f"invalid gender '{gender}'. "
                    "Use MALE, FEMALE or OTHER."
                )

            if not school_name:

                errors.append(
                    f"Row {row_number}: "
                    "school is required."
                )

            if not current_class:

                errors.append(
                    f"Row {row_number}: "
                    "current_class is required."
                )

            if not parent_name:

                errors.append(
                    f"Row {row_number}: "
                    "parent_name is required."
                )

            # -------------------------------------------------
            # FIND SCHOOL
            # -------------------------------------------------

            school = None

            if school_name:

                school = (
                    School.objects
                    .filter(
                        name__iexact=school_name
                    )
                    .first()
                )

                if not school:

                    errors.append(
                        f"Row {row_number}: "
                        f"school '{school_name}' "
                        "was not found."
                    )

            # -------------------------------------------------
            # DUPLICATE ADMISSION NUMBER
            # -------------------------------------------------

            if admission_number:

                if admission_number in uploaded_admission_numbers:

                    errors.append(
                        f"Row {row_number}: "
                        f"admission number "
                        f"'{admission_number}' "
                        "is duplicated in the uploaded file."
                    )

                else:

                    uploaded_admission_numbers.add(
                        admission_number
                    )

                if Student.objects.filter(
                    admission_number=admission_number
                ).exists():

                    errors.append(
                        f"Row {row_number}: "
                        "admission number "
                        f"'{admission_number}' "
                        "already exists."
                    )

            # -------------------------------------------------
            # DATE OF BIRTH
            # -------------------------------------------------

            date_of_birth = None

            dob_value = row.get(
                "date_of_birth"
            )

            if dob_value:

                if isinstance(
                    dob_value,
                    datetime
                ):

                    date_of_birth = (
                        dob_value.date()
                    )

                elif hasattr(
                    dob_value,
                    "year"
                ) and hasattr(
                    dob_value,
                    "month"
                ):

                    try:

                        date_of_birth = (
                            dob_value.date()
                            if hasattr(
                                dob_value,
                                "date"
                            )
                            else dob_value
                        )

                    except Exception:

                        date_of_birth = None

                else:

                    dob_string = str(
                        dob_value
                    ).strip()

                    try:

                        date_of_birth = (
                            datetime.strptime(
                                dob_string,
                                "%Y-%m-%d"
                            ).date()
                        )

                    except ValueError:

                        errors.append(
                            f"Row {row_number}: "
                            "date_of_birth must "
                            "be YYYY-MM-DD."
                        )

            # -------------------------------------------------
            # ADMISSION DATE
            # -------------------------------------------------

            admission_date = None

            admission_date_value = row.get(
                "admission_date"
            )

            if admission_date_value:

                if isinstance(
                    admission_date_value,
                    datetime
                ):

                    admission_date = (
                        admission_date_value.date()
                    )

                elif hasattr(
                    admission_date_value,
                    "year"
                ) and hasattr(
                    admission_date_value,
                    "month"
                ):

                    try:

                        admission_date = (
                            admission_date_value.date()
                            if hasattr(
                                admission_date_value,
                                "date"
                            )
                            else admission_date_value
                        )

                    except Exception:

                        admission_date = None

                else:

                    admission_date_string = str(
                        admission_date_value
                    ).strip()

                    try:

                        admission_date = (
                            datetime.strptime(
                                admission_date_string,
                                "%Y-%m-%d"
                            ).date()
                        )

                    except ValueError:

                        errors.append(
                            f"Row {row_number}: "
                            "admission_date must "
                            "be YYYY-MM-DD."
                        )

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