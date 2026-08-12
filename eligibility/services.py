from decimal import Decimal

from students.models import Student
from academics.models import AcademicRecord
from .models import EligibilityRecord, BenefitType


def get_latest_academic_record(student, academic_year=None):
    records = AcademicRecord.objects.filter(student=student)

    if academic_year:
        records = records.filter(academic_year=academic_year)

    return records.order_by("-created_at").first()


def is_class_number(class_or_course, number):
    value = class_or_course.lower().strip()

    return (
        value == f"class {number}"
        or value == str(number)
        or value == f"standard {number}"
    )


def is_school_class(class_or_course):
    value = class_or_course.lower().strip()

    for number in range(1, 11):
        if is_class_number(value, number):
            return number

    return None


def get_percentage(record):
    if record is None:
        return Decimal("0")

    if record.percentage is not None:
        return Decimal(str(record.percentage))

    if (
        record.marks_obtained is not None
        and record.total_marks is not None
        and record.total_marks > 0
    ):
        return (
            Decimal(str(record.marks_obtained))
            / Decimal(str(record.total_marks))
        ) * Decimal("100")

    return Decimal("0")


def create_or_update_eligibility(
    student,
    benefit_type,
    academic_year,
    eligible,
    selection_rank=None,
    reason="",
):
    record, created = EligibilityRecord.objects.update_or_create(
        student=student,
        benefit_type=benefit_type,
        academic_year=academic_year,
        defaults={
            "eligible": eligible,
            "selection_rank": selection_rank,
            "reason": reason,
        },
    )

    return record


# =========================================================
# BOOK ELIGIBILITY
# Class 1 to Class 10
# =========================================================

def generate_book_eligibility(student, academic_record):
    class_number = is_school_class(
        academic_record.class_or_course
    )

    if class_number and 1 <= class_number <= 10:
        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.BOOK,
            academic_year=academic_record.academic_year,
            eligible=True,
            reason=f"Student is studying in Class {class_number}.",
        )

    return None


# =========================================================
# WORKBOOK ELIGIBILITY
# Class 10
# =========================================================

def generate_workbook_eligibility(student, academic_record):
    if is_class_number(
        academic_record.class_or_course,
        10,
    ):
        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.WORKBOOK,
            academic_year=academic_record.academic_year,
            eligible=True,
            reason="Student is studying in Class 10.",
        )

    return None


# =========================================================
# TOP 10 CLASS 10 STUDENTS
# Study Kit
# =========================================================

def get_top_class_10_students(academic_year):
    records = AcademicRecord.objects.filter(
        academic_year=academic_year
    )

    class_10_records = []

    for record in records:
        if is_class_number(
            record.class_or_course,
            10,
        ):
            class_10_records.append(record)

    class_10_records.sort(
        key=get_percentage,
        reverse=True,
    )

    return class_10_records[:10]


def generate_study_kit_eligibility(academic_year):
    top_records = get_top_class_10_students(
        academic_year
    )

    for rank, record in enumerate(top_records, start=1):
        create_or_update_eligibility(
            student=record.student,
            benefit_type=BenefitType.STUDY_KIT,
            academic_year=academic_year,
            eligible=True,
            selection_rank=rank,
            reason=(
                f"Top 10 Class 10 student. "
                f"Selection rank: {rank}."
            ),
        )


# =========================================================
# STUDY KIT CONTINUATION
# Continue up to 2nd PUC
# =========================================================

def generate_study_kit_continuation(
    student,
    academic_record,
):
    value = academic_record.class_or_course.lower().strip()

    is_first_puc = (
        "1st puc" in value
        or "1st pu" in value
        or "first puc" in value
        or "first pu" in value
    )

    is_second_puc = (
        "2nd puc" in value
        or "2nd pu" in value
        or "second puc" in value
        or "second pu" in value
    )

    if not (is_first_puc or is_second_puc):
        return None

    previously_selected = EligibilityRecord.objects.filter(
        student=student,
        benefit_type=BenefitType.STUDY_KIT,
        eligible=True,
    ).exclude(
        academic_year=academic_record.academic_year
    ).exists()

    if previously_selected:
        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.STUDY_KIT,
            academic_year=academic_record.academic_year,
            eligible=True,
            reason=(
                "Student was previously selected for a "
                "study kit and continues to receive the "
                "study kit through PUC."
            ),
        )

    return None


# =========================================================
# TOP 10 SECOND PUC STUDENTS
# Laptop
# =========================================================

def get_top_puc_students(academic_year):
    records = AcademicRecord.objects.filter(
        academic_year=academic_year
    )

    puc_records = []

    for record in records:
        value = record.class_or_course.lower().strip()

        if (
            "2nd puc" in value
            or "2nd pu" in value
            or "second puc" in value
            or "second pu" in value
        ):
            puc_records.append(record)

    puc_records.sort(
        key=get_percentage,
        reverse=True,
    )

    return puc_records[:10]


def generate_laptop_eligibility(academic_year):
    top_records = get_top_puc_students(
        academic_year
    )

    for rank, record in enumerate(top_records, start=1):
        create_or_update_eligibility(
            student=record.student,
            benefit_type=BenefitType.LAPTOP,
            academic_year=academic_year,
            eligible=True,
            selection_rank=rank,
            reason=(
                f"Top 10 second PUC student. "
                f"Selection rank: {rank}."
            ),
        )


# =========================================================
# INTERNSHIP
# Degree students
# =========================================================

def generate_internship_eligibility(
    student,
    academic_record,
):
    value = academic_record.class_or_course.lower().strip()

    if "degree" in value:
        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.INTERNSHIP,
            academic_year=academic_record.academic_year,
            eligible=True,
            reason=(
                "Degree student identified as an "
                "internship candidate."
            ),
        )

    return None


# =========================================================
# GENERATE ELIGIBILITY FOR ONE STUDENT
# =========================================================

def generate_student_eligibility(
    student,
    academic_year,
):
    academic_record = get_latest_academic_record(
        student,
        academic_year,
    )

    if not academic_record:
        return []

    results = []

    book = generate_book_eligibility(
        student,
        academic_record,
    )

    if book:
        results.append(book)

    workbook = generate_workbook_eligibility(
        student,
        academic_record,
    )

    if workbook:
        results.append(workbook)

    study_kit = generate_study_kit_continuation(
        student,
        academic_record,
    )

    if study_kit:
        results.append(study_kit)

    internship = generate_internship_eligibility(
        student,
        academic_record,
    )

    if internship:
        results.append(internship)

    return results


# =========================================================
# GENERATE ELIGIBILITY FOR ALL ACTIVE STUDENTS
# =========================================================

def generate_all_eligibility(academic_year):
    students = Student.objects.filter(
        status=Student.Status.ACTIVE
    )

    for student in students:
        generate_student_eligibility(
            student,
            academic_year,
        )

    # Top 10 Class 10 → Study Kit
    generate_study_kit_eligibility(
        academic_year
    )

    # Top 10 2nd PUC → Laptop
    generate_laptop_eligibility(
        academic_year
    )