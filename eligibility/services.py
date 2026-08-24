from decimal import Decimal
import re

from students.models import Student
from academics.models import AcademicRecord
from .models import EligibilityRecord, BenefitType


# =========================================================
# BASIC HELPERS
# =========================================================

def get_latest_academic_record(student, academic_year=None):
    """Fetch the latest academic record for a student, optionally filtered by academic year"""
    records = AcademicRecord.objects.filter(student=student)
    if academic_year:
        records = records.filter(academic_year=academic_year)
    return records.order_by("-created_at").first()


def parse_class_number(class_or_course):
    """
    Parse school class/standard numbers only.

    PUC, Diploma and ITI are higher/pre-university courses
    and must not be interpreted as school classes.
    """
    if not class_or_course:
        return None

    val = str(class_or_course).lower().strip()

    # PUC/Diploma/ITI are NOT school classes.
    if any(term in val for term in [
        "puc",
        "pre-university",
        "pre university",
        "diploma",
        "iti",
    ]):
        return None

    roman_map = {
        "x": 10,
        "ix": 9,
        "viii": 8,
        "vii": 7,
        "vi": 6,
        "v": 5,
        "iv": 4,
        "iii": 3,
        "ii": 2,
        "i": 1,
    }

    for r, num in roman_map.items():
        if val in [
            r,
            f"class {r}",
            f"standard {r}",
            f"std {r}",
        ]:
            return num

    # Match digits 1-10.
    match = re.search(r"\b(10|[1-9])\b", val)
    if match:
        return int(match.group(1))

    # Match ordinal values such as 5th, 10th.
    match_ord = re.search(r"\b(10|[1-9])(st|nd|rd|th)\b", val)
    if match_ord:
        return int(match_ord.group(1))

    return None

def is_class_number(class_or_course, number):
    parsed = parse_class_number(class_or_course)
    return parsed == number


def is_school_class(class_or_course):
    return parse_class_number(class_or_course)

def normalize_course(value):
    return (value or "").lower().strip()


def is_first_puc(class_or_course):
    if not class_or_course:
        return False
    val = str(class_or_course).lower().strip()
    return any(term in val for term in ["1st puc", "1st pu", "first puc", "puc 1", "puc i", "class 11", "11th", "std 11"])


def is_second_puc(class_or_course):
    if not class_or_course:
        return False
    val = str(class_or_course).lower().strip()
    return any(term in val for term in ["2nd puc", "2nd pu", "second puc", "puc 2", "puc ii", "class 12", "12th", "std 12"])


def is_degree_student(class_or_course):
    if not class_or_course:
        return False
    val = str(class_or_course).lower().strip()
    return any(term in val for term in ["degree", "bca", "bsc", "b.sc", "bcom", "b.com", "btech", "b.tech", "be", "b.e", "ba", "b.a", "college", "undergraduate", "diploma"])


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
# 1. BOOK ELIGIBILITY (Class 1 to Class 10)
# =========================================================

def generate_book_eligibility(student, academic_record):
    class_number = is_school_class(academic_record.class_or_course)
    if class_number and 1 <= class_number <= 10:
        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.BOOK,
            academic_year=academic_record.academic_year,
            eligible=True,
            reason=f"Enrolled in Class {class_number} (eligible for standard books).",
        )
    return None


# =========================================================
# 2. WORKBOOK ELIGIBILITY (Class 10 Board Prep)
# =========================================================

def generate_workbook_eligibility(student, academic_record):
    if is_class_number(academic_record.class_or_course, 10):
        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.WORKBOOK,
            academic_year=academic_record.academic_year,
            eligible=True,
            reason="Enrolled in Class 10 (eligible for board exam preparation workbooks).",
        )
    return None


# =========================================================
# 3. STUDY KIT ELIGIBILITY (Top 10 Class 10 Students)
# =========================================================

def get_top_class_10_students(academic_year, limit=10):
    records = AcademicRecord.objects.filter(academic_year=academic_year)
    class_10_records = [
        rec for rec in records
        if is_class_number(rec.class_or_course, 10)
    ]
    class_10_records.sort(key=get_percentage, reverse=True)
    return class_10_records[:limit]


def generate_study_kit_eligibility(academic_year, limit=10):
    top_records = get_top_class_10_students(academic_year, limit=limit)
    count = 0
    for rank, record in enumerate(top_records, start=1):
        pct = get_percentage(record)
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


def generate_study_kit_eligibility(academic_year, limit=10):
    top_records = get_top_class_10_students(academic_year)
    count = 0
    for rank, record in enumerate(top_records[:limit], start=1):
        pct = get_percentage(record)
        create_or_update_eligibility(
            student=record.student,
            benefit_type=BenefitType.STUDY_KIT,
            academic_year=academic_year,
            eligible=True,
            selection_rank=rank,
            reason=f"Top {limit} Merit Scholar in Class 10 (Rank #{rank} with {pct:.2f}% score).",
        )
        count += 1
    return count


# =========================================================
# 4. STUDY KIT CONTINUATION (1st & 2nd PUC / Pre-University)
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

def generate_study_kit_continuation(student, academic_record):
    if not is_pre_university_course(academic_record.class_or_course):
        return None

    # Check if student was awarded Study Kit in any previous academic year
    previously_selected = EligibilityRecord.objects.filter(
        student=student,
        benefit_type=BenefitType.STUDY_KIT,
        eligible=True,
    ).exclude(
        academic_year=academic_record.academic_year
    ).exists()

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

def calculate_study_kit_continuation_batch(academic_year):
    active_students = Student.objects.filter(status=Student.Status.ACTIVE)
    count = 0
    for student in active_students:
        rec = get_latest_academic_record(student, academic_year)
        if rec:
            res = generate_study_kit_continuation(student, rec)
            if res:
                count += 1
    return count


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

def get_top_puc_students(academic_year, limit=10):
    records = AcademicRecord.objects.filter(academic_year=academic_year)
    puc_records = [
        rec for rec in records
        if is_second_puc(rec.class_or_course)
    ]
    puc_records.sort(key=get_percentage, reverse=True)
    return puc_records[:limit]


def generate_laptop_eligibility(academic_year, limit=10):
    top_records = get_laptop_qualifying_students(academic_year)
    count = 0
    for rank, record in enumerate(top_records[:limit], start=1):
        pct = get_percentage(record)
        create_or_update_eligibility(
            student=record.student,
            benefit_type=BenefitType.LAPTOP,
            academic_year=academic_year,
            eligible=True,
            selection_rank=rank,
            reason=f"Top {limit} Merit Laptop Scholar in 2nd PUC / Diploma Qualifying Stage (Rank #{rank} with {pct:.2f}% score).",
        )
        count += 1
    return count


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
            reason=f"Higher education / Degree candidate ({academic_record.class_or_course}) identified for Aequs Industrial Internship Program.",
        )
    return None


# =========================================================
# GENERATE ELIGIBILITY FOR A SINGLE STUDENT
# =========================================================

def generate_student_eligibility(student, academic_year):
    academic_record = get_latest_academic_record(student, academic_year)
def generate_student_eligibility(
    student,
    academic_year,
):

    academic_record = get_latest_academic_record(
        student,
        academic_year,
    )

    if not academic_record:
        current_cls = student.current_class or ""
        class_number = parse_class_number(current_cls)
        results = []
        if class_number and 1 <= class_number <= 10:
            b = create_or_update_eligibility(
                student=student,
                benefit_type=BenefitType.BOOK,
                academic_year=academic_year,
                eligible=True,
                reason=f"Current enrolled class is {current_cls}.",
            )
            results.append(b)
            if class_number == 10:
                w = create_or_update_eligibility(
                    student=student,
                    benefit_type=BenefitType.WORKBOOK,
                    academic_year=academic_year,
                    eligible=True,
                    reason=f"Current enrolled class is {current_cls} (Class 10 Workbook).",
                )
                results.append(w)
        elif is_degree_student(current_cls):
            i = create_or_update_eligibility(
                student=student,
                benefit_type=BenefitType.INTERNSHIP,
                academic_year=academic_year,
                eligible=True,
                reason=f"Current enrolled program is {current_cls}.",
            )
            results.append(i)
        return results

    results = []

    # Books (Class 1 to 10)
    book = generate_book_eligibility(student, academic_record)
    if book:
        results.append(book)

    # Workbooks (Class 10)
    workbook = generate_workbook_eligibility(student, academic_record)
    if workbook:
        results.append(workbook)

    # Study Kit continuation (PUC)
    study_kit = generate_study_kit_continuation(student, academic_record)
    if study_kit:
        results.append(study_kit)

    # Internship (Degree)
    internship = generate_internship_eligibility(student, academic_record)
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
# EVALUATE FULL 360 PROFILE FOR PREVIEW
# =========================================================

def get_student_eligibility_profile(student, academic_year=None):
    """
    Returns an evaluation profile for a student covering all 5 benefit types
    along with their academic standing and existing database records.
    """
    academic_record = get_latest_academic_record(student, academic_year)
    effective_class = academic_record.class_or_course if academic_record else (student.current_class or "Unknown")
    class_num = parse_class_number(effective_class)
    pct = float(get_percentage(academic_record)) if academic_record else 0.0

    # Fetch existing DB records
    db_records_qs = EligibilityRecord.objects.filter(student=student)
    if academic_year:
        db_records_qs = db_records_qs.filter(academic_year=academic_year)
    db_records = {r.benefit_type: r for r in db_records_qs}

    # Evaluate potential eligibility for each
    benefits_eval = []
    
    # 1. Books
    book_rec = db_records.get(BenefitType.BOOK)
    book_auto = (class_num is not None and 1 <= class_num <= 10)
    benefits_eval.append({
        "benefit_type": BenefitType.BOOK,
        "benefit_display": "Books (Class 1-10)",
        "icon": "📚",
        "is_eligible": book_rec.eligible if book_rec else book_auto,
        "record_exists": book_rec is not None,
        "selection_rank": book_rec.selection_rank if book_rec else None,
        "reason": book_rec.reason if book_rec else ("Eligible: Enrolled in Class 1-10" if book_auto else "Ineligible: Not in standard 1-10 range"),
        "rule_summary": "Standard textbook package for all primary & secondary students (Class 1 - 10).",
    })

    # 2. Workbooks
    wb_rec = db_records.get(BenefitType.WORKBOOK)
    wb_auto = (class_num == 10)
    benefits_eval.append({
        "benefit_type": BenefitType.WORKBOOK,
        "benefit_display": "Workbook (Class 10)",
        "icon": "📝",
        "is_eligible": wb_rec.eligible if wb_rec else wb_auto,
        "record_exists": wb_rec is not None,
        "selection_rank": wb_rec.selection_rank if wb_rec else None,
        "reason": wb_rec.reason if wb_rec else ("Eligible: Enrolled in Class 10 Board preparation" if wb_auto else "Ineligible: Available only for Class 10"),
        "rule_summary": "Intensive revision and STEM practice workbook for 10th standard board candidates.",
    })

    # 3. Study Kit
    sk_rec = db_records.get(BenefitType.STUDY_KIT)
    is_puc = is_first_puc(effective_class) or is_second_puc(effective_class)
    prev_sk = EligibilityRecord.objects.filter(student=student, benefit_type=BenefitType.STUDY_KIT, eligible=True).exclude(academic_year=academic_year).exists()
    sk_auto = (class_num == 10 and pct >= 80.0) or (is_puc and prev_sk)
    benefits_eval.append({
        "benefit_type": BenefitType.STUDY_KIT,
        "benefit_display": "Study Kit (Merit & PUC Continuation)",
        "icon": "🎒",
        "is_eligible": sk_rec.eligible if sk_rec else sk_auto,
        "record_exists": sk_rec is not None,
        "selection_rank": sk_rec.selection_rank if sk_rec else None,
        "reason": sk_rec.reason if sk_rec else ("Merit candidate: High academic ranking or PUC continuation" if sk_auto else "Requires Top 10 rank in Class 10 or PUC continuation grant"),
        "rule_summary": "Awarded to Top 10 Class 10 rank holders and renewed through 1st & 2nd PUC.",
    })

    # 4. Laptop
    lp_rec = db_records.get(BenefitType.LAPTOP)
    lp_auto = is_second_puc(effective_class) and pct >= 85.0
    benefits_eval.append({
        "benefit_type": BenefitType.LAPTOP,
        "benefit_display": "Laptop Scholarship (Top 10 2nd PUC)",
        "icon": "💻",
        "is_eligible": lp_rec.eligible if lp_rec else lp_auto,
        "record_exists": lp_rec is not None,
        "selection_rank": lp_rec.selection_rank if lp_rec else None,
        "reason": lp_rec.reason if lp_rec else ("High merit 2nd PUC scholar eligible for laptop grant" if lp_auto else "Requires Top 10 merit rank in 2nd PUC state examinations"),
        "rule_summary": "Top 10 highest-scoring 2nd PUC students transitioning to college.",
    })

    # 5. Internship
    in_rec = db_records.get(BenefitType.INTERNSHIP)
    in_auto = is_degree_student(effective_class)
    benefits_eval.append({
        "benefit_type": BenefitType.INTERNSHIP,
        "benefit_display": "Internship (Degree Students)",
        "icon": "💼",
        "is_eligible": in_rec.eligible if in_rec else in_auto,
        "record_exists": in_rec is not None,
        "selection_rank": in_rec.selection_rank if in_rec else None,
        "reason": in_rec.reason if in_rec else ("Degree candidate eligible for Aequs CSR internship track" if in_auto else "Reserved for undergraduate and technical degree candidates"),
        "rule_summary": "Corporate and industrial internship program for degree scholars.",
    })

    return {
        "student_id": student.id,
        "student_name": student.student_name,
        "admission_number": student.admission_number,
        "school_name": student.school.name if student.school else "General",
        "current_class": effective_class,
        "percentage": pct,
        "academic_year": academic_year or (academic_record.academic_year if academic_record else "2026-27"),
        "benefits": benefits_eval,
    }


# =========================================================
# GENERATE ELIGIBILITY FOR ALL ACTIVE STUDENTS (BATCH ENGINE)
# =========================================================

def generate_all_eligibility(academic_year, target_benefits=None):
    """
    Runs the automated eligibility evaluation engine for an academic year.
    Returns metrics dict on generated / updated records.
    """
    students = Student.objects.filter(status=Student.Status.ACTIVE)
    
    do_all = not target_benefits or "ALL" in target_benefits
    do_books = do_all or BenefitType.BOOK in target_benefits
    do_workbooks = do_all or BenefitType.WORKBOOK in target_benefits
    do_study_kit = do_all or BenefitType.STUDY_KIT in target_benefits
    do_laptops = do_all or BenefitType.LAPTOP in target_benefits
    do_internships = do_all or BenefitType.INTERNSHIP in target_benefits

    processed_students = 0
    books_count = 0
    workbooks_count = 0
    study_kit_cont_count = 0
    internships_count = 0

    for student in students:
        processed_students += 1
        rec = get_latest_academic_record(student, academic_year)
        
        # Books
        if do_books:
            if rec:
                b = generate_book_eligibility(student, rec)
                if b and b.eligible:
                    books_count += 1
            else:
                c_num = parse_class_number(student.current_class)
                if c_num and 1 <= c_num <= 10:
                    create_or_update_eligibility(
                        student=student,
                        benefit_type=BenefitType.BOOK,
                        academic_year=academic_year,
                        eligible=True,
                        reason=f"Current enrolled class is {student.current_class}.",
                    )
                    books_count += 1

        # Workbooks
        if do_workbooks:
            if rec:
                w = generate_workbook_eligibility(student, rec)
                if w and w.eligible:
                    workbooks_count += 1
            else:
                if is_class_number(student.current_class, 10):
                    create_or_update_eligibility(
                        student=student,
                        benefit_type=BenefitType.WORKBOOK,
                        academic_year=academic_year,
                        eligible=True,
                        reason=f"Current enrolled class is {student.current_class} (Class 10 Workbook).",
                    )
                    workbooks_count += 1

        # Study Kit continuation
        if do_study_kit:
            if rec:
                sk = generate_study_kit_continuation(student, rec)
                if sk and sk.eligible:
                    study_kit_cont_count += 1

        # Internships
        if do_internships:
            if rec:
                in_res = generate_internship_eligibility(student, rec)
                if in_res and in_res.eligible:
                    internships_count += 1
            else:
                if is_degree_student(student.current_class):
                    create_or_update_eligibility(
                        student=student,
                        benefit_type=BenefitType.INTERNSHIP,
                        academic_year=academic_year,
                        eligible=True,
                        reason=f"Current enrolled program is {student.current_class}.",
                    )
                    internships_count += 1

    # Top 10 Class 10 → Study Kit
    study_kit_top_count = 0
    if do_study_kit:
        study_kit_top_count = generate_study_kit_eligibility(academic_year)

    # Top 10 2nd PUC → Laptop
    laptop_count = 0
    if do_laptops:
        laptop_count = generate_laptop_eligibility(academic_year)

    total_eligible = EligibilityRecord.objects.filter(
        academic_year=academic_year,
        eligible=True,
    ).count()

    return {
        "academic_year": academic_year,
        "processed_students": processed_students,
        "books_count": books_count,
        "workbooks_count": workbooks_count,
        "study_kit_top_count": study_kit_top_count,
        "study_kit_continuation_count": study_kit_cont_count,
        "study_kit_total": study_kit_top_count + study_kit_cont_count,
        "laptop_count": laptop_count,
        "internships_count": internships_count,
        "total_eligible_records": total_eligible,
    }


# =========================================================
# ALIASES FOR MANAGEMENT COMMANDS & EXTERNAL CONSUMERS
# =========================================================

def calculate_student_eligibility(student, academic_year):
    return generate_student_eligibility(student, academic_year)

def calculate_study_kit_eligibility(academic_year, limit=10):
    return generate_study_kit_eligibility(academic_year, limit=limit)

def calculate_study_kit_continuation(academic_year):
    return calculate_study_kit_continuation_batch(academic_year)

def calculate_laptop_eligibility(academic_year, limit=10):
    return generate_laptop_eligibility(academic_year, limit=limit)
# Legacy alias pointing to main batch engine
def run_legacy_generate_all_eligibility(academic_year):
    return generate_all_eligibility(academic_year)
