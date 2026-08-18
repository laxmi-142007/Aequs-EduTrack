from decimal import Decimal

from students.models import Student
from academics.models import AcademicRecord
from .models import EligibilityRecord, BenefitType


# =========================================================
# BASIC HELPERS
# =========================================================

def get_latest_academic_record(student, academic_year=None):
    records = AcademicRecord.objects.filter(student=student)

    if academic_year:
        records = records.filter(
            academic_year=academic_year
        )

    return records.order_by("-created_at").first()


def normalize_course(value):
    return (value or "").lower().strip()


def is_class_number(class_or_course, number):
    value = normalize_course(class_or_course)

    return value in (
        f"class {number}",
        str(number),
        f"standard {number}",
    )


def is_school_class(class_or_course):
    value = normalize_course(class_or_course)

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
# BOOKS
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
            reason=(
                f"Student is studying in Class {class_number}."
            ),
        )

    return None


# =========================================================
# WORKBOOK
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
# TOP 10 CLASS 10
# TOP 10 RECEIVE STUDY KIT
# =========================================================

def get_top_class_10_students(academic_year):

    records = AcademicRecord.objects.filter(
        academic_year=academic_year
    ).select_related("student")

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

    for rank, record in enumerate(
        top_records,
        start=1,
    ):

        create_or_update_eligibility(
            student=record.student,
            benefit_type=BenefitType.STUDY_KIT,
            academic_year=academic_year,
            eligible=True,
            selection_rank=rank,
            reason=(
                "Top 10 Class 10 student. "
                f"Study Kit selection rank: {rank}."
            ),
        )


# =========================================================
# PRE-UNIVERSITY COURSES
#
# Students selected in Class 10 continue receiving
# Study Kit during their pre-university course.
#
# Examples:
#   1st PUC
#   2nd PUC
#   Diploma
#   ITI
#   Other pre-university courses
# =========================================================

def is_puc_course(class_or_course):

    value = normalize_course(class_or_course)

    return (
        "1st puc" in value
        or "1st pu" in value
        or "first puc" in value
        or "first pu" in value
        or "2nd puc" in value
        or "2nd pu" in value
        or "second puc" in value
        or "second pu" in value
    )


def is_diploma_course(class_or_course):

    value = normalize_course(class_or_course)

    return "diploma" in value


def is_iti_course(class_or_course):

    value = normalize_course(class_or_course)

    return "iti" in value


def is_pre_university_course(class_or_course):

    return (
        is_puc_course(class_or_course)
        or is_diploma_course(class_or_course)
        or is_iti_course(class_or_course)
    )


def generate_study_kit_continuation(
    student,
    academic_record,
):

    if not is_pre_university_course(
        academic_record.class_or_course
    ):
        return None

    previously_selected = (
        EligibilityRecord.objects.filter(
            student=student,
            benefit_type=BenefitType.STUDY_KIT,
            eligible=True,
        )
        .exclude(
            academic_year=academic_record.academic_year
        )
        .exists()
    )

    if not previously_selected:
        return None

    return create_or_update_eligibility(
        student=student,
        benefit_type=BenefitType.STUDY_KIT,
        academic_year=academic_record.academic_year,
        eligible=True,
        reason=(
            "Student was selected in the Class 10 Top 10 "
            "and continues to receive Study Kit during "
            "the pre-university course."
        ),
    )


# =========================================================
# LAPTOP QUALIFYING STAGE
#
# The final qualifying students are:
#
#   1. 2nd PUC
#   2. Final-year Diploma
#
# These two groups are compared together by percentage.
# Top 10 become laptop candidates.
# =========================================================

def is_second_puc(class_or_course):

    value = normalize_course(class_or_course)

    return (
        "2nd puc" in value
        or "2nd pu" in value
        or "second puc" in value
        or "second pu" in value
    )


def is_final_year_diploma(record):

    value = normalize_course(
        record.class_or_course
    )

    if "diploma" not in value:
        return False

    # If the course explicitly contains a year number,
    # identify 3rd year as the final Diploma year.
    return (
        "3rd year" in value
        or "third year" in value
        or "3rd" in value
        or "third" in value
    )


def get_laptop_qualifying_students(academic_year):

    records = AcademicRecord.objects.filter(
        academic_year=academic_year
    ).select_related("student")

    qualifying_records = []

    for record in records:

        if is_second_puc(
            record.class_or_course
        ):
            qualifying_records.append(record)

        elif is_final_year_diploma(record):
            qualifying_records.append(record)

    qualifying_records.sort(
        key=get_percentage,
        reverse=True,
    )

    return qualifying_records[:10]


def generate_laptop_eligibility(academic_year):

    top_records = get_laptop_qualifying_students(
        academic_year
    )

    for rank, record in enumerate(
        top_records,
        start=1,
    ):

        create_or_update_eligibility(
            student=record.student,
            benefit_type=BenefitType.LAPTOP,
            academic_year=academic_year,
            eligible=True,
            selection_rank=rank,
            reason=(
                "Top 10 student among 2nd PUC and "
                "final-year Diploma students. "
                f"Laptop selection rank: {rank}."
            ),
        )


# =========================================================
# LAPTOP DISTRIBUTION STAGE
#
# Laptop is given when the selected student enters Degree.
#
# Regular Degree student:
#     Degree 1st year
#
# Diploma student:
#     BE 2nd year through lateral entry
#
# NOTE:
# The Top 10 ranking is determined at the qualifying
# stage above. This function identifies the stage where
# the laptop should actually be distributed.
# =========================================================

def is_degree_first_year(class_or_course):

    value = normalize_course(class_or_course)

    return (
        (
            "degree" in value
            and (
                "1st year" in value
                or "first year" in value
                or "1st" in value
                or "first" in value
            )
        )
        or (
            "degree 1" in value
        )
    )


def is_be_second_year(class_or_course):

    value = normalize_course(class_or_course)

    return (
        (
            "be" in value
            and (
                "2nd year" in value
                or "second year" in value
                or "2nd" in value
                or "second" in value
            )
        )
        or (
            "b.e" in value
            and (
                "2nd year" in value
                or "second year" in value
            )
        )
    )


def generate_laptop_distribution_eligibility(
    student,
    academic_record,
):

    if not (
        is_degree_first_year(
            academic_record.class_or_course
        )
        or is_be_second_year(
            academic_record.class_or_course
        )
    ):
        return None

    previous_laptop = (
        EligibilityRecord.objects.filter(
            student=student,
            benefit_type=BenefitType.LAPTOP,
            eligible=True,
        )
        .exclude(
            academic_year=academic_record.academic_year
        )
        .exists()
    )

    if not previous_laptop:
        return None

    return create_or_update_eligibility(
        student=student,
        benefit_type=BenefitType.LAPTOP,
        academic_year=academic_record.academic_year,
        eligible=True,
        reason=(
            "Previously selected student has entered "
            "the Degree stage and is eligible to receive "
            "the laptop."
        ),
    )


# =========================================================
# INTERNSHIP
#
# Degree students can be internship candidates.
# =========================================================

def generate_internship_eligibility(
    student,
    academic_record,
):

    value = normalize_course(
        academic_record.class_or_course
    )

    if "degree" in value or "b.e" in value or "be " in value:

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

    laptop_distribution = (
        generate_laptop_distribution_eligibility(
            student,
            academic_record,
        )
    )

    if laptop_distribution:
        results.append(laptop_distribution)

    internship = generate_internship_eligibility(
        student,
        academic_record,
    )

    if internship:
        results.append(internship)

    return results


# =========================================================
# GENERATE ALL ELIGIBILITY
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

    # -----------------------------------------
    # Class 10 Top 10 -> Study Kit
    # -----------------------------------------

    generate_study_kit_eligibility(
        academic_year
    )

    # -----------------------------------------
    # 2nd PUC + Final Diploma -> Top 10 Laptop
    # -----------------------------------------

    generate_laptop_eligibility(
        academic_year
    )
