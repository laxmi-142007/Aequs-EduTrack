import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from .models import AcademicRecord
from students.models import Student
from schools.models import School


def _record_to_dict(rec):
    return {
        "id": rec.id,
        "student_id": rec.student.id if rec.student else None,
        "student_name": rec.student.student_name if rec.student else "Unknown",
        "admission_number": rec.student.admission_number if rec.student else "",
        "school_name": rec.student.school.name if rec.student and rec.student.school else "General",
        "academic_year": rec.academic_year,
        "class_or_course": rec.class_or_course,
        "percentage": float(rec.percentage) if rec.percentage is not None else None,
        "marks_obtained": float(rec.marks_obtained) if rec.marks_obtained is not None else None,
        "total_marks": float(rec.total_marks) if rec.total_marks is not None else None,
        "rank": rec.rank,
        "promotion_status": rec.promotion_status or "Promoted",
        "transfer_school": rec.transfer_school or "",
        "remarks": rec.remarks or "",
        "created_at": rec.created_at.strftime("%Y-%m-%d"),
    }


def _ensure_initial_data():
    if not AcademicRecord.objects.exists():
        # Ensure at least 1 default school
        school = School.objects.first()
        if not school:
            school = School.objects.create(
                name="Govt. Model High School",
                udise_code="29010200301",
                district="Bangalore Urban",
                village="Jayanagar",
            )

        sample_data = [
            {"name": "Aarav Sharma", "adm": "ADM-2023-001", "year": "2023-2024", "class": "Class 5", "pct": 92.5, "rank": 1, "status": "Promoted", "transfer": ""},
            {"name": "Diya Patel", "adm": "ADM-2023-002", "year": "2023-2024", "class": "Class 5", "pct": 88.0, "rank": 3, "status": "Promoted", "transfer": ""},
            {"name": "Rohan Gupta", "adm": "ADM-2023-003", "year": "2023-2024", "class": "Class 5", "pct": 45.0, "rank": 32, "status": "Conditional", "transfer": ""},
            {"name": "Sanya Iyer", "adm": "ADM-2023-004", "year": "2023-2024", "class": "Class 5", "pct": 32.0, "rank": 40, "status": "Not Promoted", "transfer": ""},
        ]

        for item in sample_data:
            st, _ = Student.objects.get_or_create(
                admission_number=item["adm"],
                defaults={
                    "student_name": item["name"],
                    "school": school,
                    "current_class": item["class"],
                    "gender": Student.Gender.MALE if "Sharma" in item["name"] or "Gupta" in item["name"] else Student.Gender.FEMALE,
                    "parent_name": "Parent of " + item["name"],
                }
            )
            AcademicRecord.objects.create(
                student=st,
                academic_year=item["year"],
                class_or_course=item["class"],
                percentage=Decimal(str(item["pct"])),
                rank=item["rank"],
                promotion_status=item["status"],
                transfer_school=item["transfer"],
            )


@ensure_csrf_cookie
def academic_portal(request):
    """
    Main Academic Record Management Portal View with 1 single sidebar.
    """
    _ensure_initial_data()
    records = AcademicRecord.objects.select_related("student", "student__school").order_by("-academic_year", "rank", "student__student_name")
    students = Student.objects.select_related("school").order_by("student_name")

    total_records = records.count()
    promoted_count = records.filter(promotion_status__iexact="Promoted").count()
    conditional_count = records.filter(promotion_status__iexact="Conditional").count()
    not_promoted_count = records.filter(promotion_status__icontains="Not").count()

    context = {
        "records": records,
        "students": students,
        "total_records": total_records,
        "promoted_count": promoted_count,
        "conditional_count": conditional_count,
        "not_promoted_count": not_promoted_count,
        "user_authenticated": request.user.is_authenticated,
        "username": request.user.username if request.user.is_authenticated else "Admin",
    }
    return render(request, "academics/portal.html", context)


def academic_list(request):
    return academic_portal(request)


# =========================================================================
# JSON REST APIs
# =========================================================================

def api_academic_records(request):
    """List academic records with optional filtering"""
    records = AcademicRecord.objects.select_related("student", "student__school").all()

    year = request.GET.get("year")
    student_class = request.GET.get("class")
    status = request.GET.get("status")
    search = request.GET.get("search")

    if year:
        records = records.filter(academic_year=year)
    if student_class:
        records = records.filter(class_or_course=student_class)
    if status:
        records = records.filter(promotion_status__iexact=status)
    if search:
        records = records.filter(student__student_name__icontains=search)

    data = [_record_to_dict(r) for r in records]
    return JsonResponse({"success": True, "records": data, "count": len(data)})


@require_http_methods(["POST"])
def api_create_academic_record(request):
    """Add or save a student academic record from Tab 2"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        student_name = data.get("studentName", "").strip()
        student_id = data.get("studentId")
        academic_year = data.get("academicYear", "").strip()
        student_class = data.get("studentClass") or data.get("class_or_course", "").strip()
        percentage = data.get("percentage")
        rank = data.get("rank")
        promotion_status = data.get("promotionDetails") or data.get("promotion_status", "Promoted").strip()
        school_transfer = data.get("schoolTransfer", "No")
        transfer_details = data.get("transferDetails") or data.get("transfer_school", "").strip()
        remarks = data.get("remarks", "").strip()

        if not student_name and not student_id:
            return JsonResponse({"success": False, "error": "Student Name is required."}, status=400)
        if not academic_year:
            return JsonResponse({"success": False, "error": "Academic Year is required."}, status=400)
        if not student_class:
            return JsonResponse({"success": False, "error": "Class is required."}, status=400)
        if percentage is None or percentage == "":
            return JsonResponse({"success": False, "error": "Percentage is required."}, status=400)

        # Resolve student
        student = None
        if student_id:
            student = Student.objects.filter(id=student_id).first()
        
        if not student and student_name:
            # Look up by name or create
            student = Student.objects.filter(student_name__iexact=student_name).first()
            if not student:
                school = School.objects.first()
                if not school:
                    school = School.objects.create(name="Govt. Model School", udise_code="29010200001", district="General")
                import random
                adm_no = f"ADM-{random.randint(1000, 9999)}"
                student = Student.objects.create(
                    student_name=student_name,
                    admission_number=adm_no,
                    school=school,
                    current_class=student_class,
                    parent_name="Parent of " + student_name,
                )

        transfer_val = transfer_details if (school_transfer == "Yes" or transfer_details) else ""

        record = AcademicRecord.objects.create(
            student=student,
            academic_year=academic_year,
            class_or_course=student_class,
            percentage=Decimal(str(percentage)),
            rank=int(rank) if rank and str(rank).isdigit() else None,
            promotion_status=promotion_status,
            transfer_school=transfer_val,
            remarks=remarks,
        )

        return JsonResponse({
            "success": True,
            "message": f"Academic record for {student.student_name} saved successfully!",
            "record": _record_to_dict(record),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_update_academic_record(request, record_id):
    """Update an existing academic record"""
    try:
        record = get_object_or_404(AcademicRecord, id=record_id)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        if "academicYear" in data:
            record.academic_year = data["academicYear"].strip()
        if "studentClass" in data:
            record.class_or_course = data["studentClass"].strip()
        if "percentage" in data and data["percentage"] != "":
            record.percentage = Decimal(str(data["percentage"]))
        if "rank" in data:
            record.rank = int(data["rank"]) if data["rank"] and str(data["rank"]).isdigit() else None
        if "promotionDetails" in data:
            record.promotion_status = data["promotionDetails"].strip()
        if "transferDetails" in data:
            record.transfer_school = data["transferDetails"].strip()

        record.save()
        return JsonResponse({
            "success": True,
            "message": "Academic record updated successfully!",
            "record": _record_to_dict(record),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_delete_academic_record(request, record_id):
    """Delete an academic record"""
    try:
        record = get_object_or_404(AcademicRecord, id=record_id)
        record.delete()
        return JsonResponse({"success": True, "message": "Academic record deleted successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def api_get_students(request):
    """Get list of active students for dropdown / autocomplete"""
    students = Student.objects.select_related("school").all().order_by("student_name")
    data = [
        {
            "id": s.id,
            "name": s.student_name,
            "admission_number": s.admission_number,
            "current_class": s.current_class,
            "school": s.school.name if s.school else "",
        }
        for s in students
    ]
    return JsonResponse({"success": True, "students": data})
from django.shortcuts import render, redirect, get_object_or_404

from .models import AcademicRecord
from .forms import AcademicRecordForm


def academic_list(request):
    records = AcademicRecord.objects.select_related("student").all()

    return render(
        request,
        "academics/academic_list.html",
        {
            "records": records,
        },
    )


def academic_create(request):
    if request.method == "POST":
        form = AcademicRecordForm(request.POST)

        if form.is_valid():
            form.save()
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
    record = get_object_or_404(AcademicRecord, pk=pk)

    if request.method == "POST":
        form = AcademicRecordForm(request.POST, instance=record)

        if form.is_valid():
            form.save()
            return redirect("academics:list")
    else:
        form = AcademicRecordForm(instance=record)

    return render(
        request,
        "academics/academic_form.html",
        {
            "form": form,
            "record": record,
        },
    )


def academic_delete(request, pk):
    record = get_object_or_404(AcademicRecord, pk=pk)

    if request.method == "POST":
        record.delete()
        return redirect("academics:list")

    return render(
        request,
        "academics/academic_confirm_delete.html",
        {
            "record": record,
        },
    )

# ============================================================================
# ACADEMIC BULK UPLOAD
# ============================================================================

import csv
import io

from django.contrib import messages
from django.db import transaction


def academic_bulk_upload(request):
    """
    Bulk upload academic records from CSV.

    Required:
        admission_number
        academic_year
        class_or_course

    Optional:
        marks_obtained
        total_marks
        percentage
        rank
        promotion_status
        transfer_school
        remarks
    """

    if request.method == "GET":
        return render(
            request,
            "academics/bulk_upload.html",
        )

    uploaded_file = request.FILES.get("academic_file")

    if not uploaded_file:
        messages.error(request, "Please select a CSV file.")
        return redirect("academics:bulk_upload")

    if not uploaded_file.name.lower().endswith(".csv"):
        messages.error(request, "Only CSV files are supported.")
        return redirect("academics:bulk_upload")

    try:
        raw_data = uploaded_file.read()

        # Support UTF-8 BOM as well as normal UTF-8.
        text = raw_data.decode("utf-8-sig")

        reader = csv.DictReader(io.StringIO(text))

        if not reader.fieldnames:
            messages.error(request, "The CSV file is empty.")
            return redirect("academics:bulk_upload")

        # Normalize column names.
        reader.fieldnames = [
            field.strip().lower().replace(" ", "_")
            if field
            else ""
            for field in reader.fieldnames
        ]

        required_columns = {
            "admission_number",
            "academic_year",
            "class_or_course",
        }

        missing = required_columns - set(reader.fieldnames)

        if missing:
            messages.error(
                request,
                "Missing required columns: "
                + ", ".join(sorted(missing)),
            )
            return redirect("academics:bulk_upload")

        created_count = 0
        updated_count = 0
        errors = []

        rows = list(reader)

        with transaction.atomic():

            for row_number, row in enumerate(rows, start=2):

                try:
                    admission_number = (
                        row.get("admission_number") or ""
                    ).strip()

                    academic_year = (
                        row.get("academic_year") or ""
                    ).strip()

                    class_or_course = (
                        row.get("class_or_course") or ""
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

                    student = (
                        Student.objects
                        .select_related("school")
                        .filter(
                            admission_number__iexact=admission_number
                        )
                        .first()
                    )

                    if not student:
                        raise ValueError(
                            f"No student found with admission number "
                            f"'{admission_number}'."
                        )

                    def clean_decimal(field_name):
                        value = (
                            row.get(field_name) or ""
                        ).strip()

                        if value == "":
                            return None

                        try:
                            return Decimal(value)
                        except Exception:
                            raise ValueError(
                                f"Invalid {field_name}: '{value}'."
                            )

                    marks_obtained = clean_decimal(
                        "marks_obtained"
                    )

                    total_marks = clean_decimal(
                        "total_marks"
                    )

                    percentage = clean_decimal(
                        "percentage"
                    )

                    rank_value = (
                        row.get("rank") or ""
                    ).strip()

                    rank = None

                    if rank_value:
                        try:
                            rank = int(rank_value)
                        except ValueError:
                            raise ValueError(
                                f"Invalid rank: '{rank_value}'."
                            )

                    promotion_status = (
                        row.get("promotion_status") or ""
                    ).strip()

                    transfer_school = (
                        row.get("transfer_school") or ""
                    ).strip()

                    remarks = (
                        row.get("remarks") or ""
                    ).strip()

                    record, created = (
                        AcademicRecord.objects
                        .get_or_create(
                            student=student,
                            academic_year=academic_year,
                            class_or_course=class_or_course,
                            defaults={
                                "marks_obtained": marks_obtained,
                                "total_marks": total_marks,
                                "percentage": percentage,
                                "rank": rank,
                                "promotion_status": promotion_status,
                                "transfer_school": transfer_school,
                                "remarks": remarks,
                            },
                        )
                    )

                    if created:
                        created_count += 1
                    else:
                        record.marks_obtained = marks_obtained
                        record.total_marks = total_marks

                        if percentage is not None:
                            record.percentage = percentage

                        record.rank = rank
                        record.promotion_status = promotion_status
                        record.transfer_school = transfer_school
                        record.remarks = remarks

                        record.save()

                        updated_count += 1

                except Exception as exc:
                    errors.append(
                        f"Row {row_number}: {exc}"
                    )

            if errors:
                raise ValueError(
                    "Upload failed because some rows contain errors."
                )

        messages.success(
            request,
            f"Upload completed successfully. "
            f"Created: {created_count}, "
            f"Updated: {updated_count}.",
        )

        return redirect("academics:bulk_upload")

    except UnicodeDecodeError:
        messages.error(
            request,
            "The CSV file is not UTF-8 encoded. "
            "Please save the CSV as UTF-8 and upload again.",
        )

    except ValueError as exc:
        messages.error(request, str(exc))

    except Exception as exc:
        messages.error(
            request,
            f"Upload failed: {exc}",
        )

    return redirect("academics:bulk_upload")
