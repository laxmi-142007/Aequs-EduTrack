from decimal import Decimal
import re

from students.models import Student
from academics.models import AcademicRecord
from .models import EligibilityRecord, BenefitType


# =========================================================
# BASIC HELPERS
# =========================================================

def get_latest_academic_record(student, academic_year=None):
    """
    Fetch the latest academic record for a student,
    optionally filtered by academic year.
    """

    records = AcademicRecord.objects.filter(
        student=student
    )

    if academic_year:
        records = records.filter(
            academic_year=academic_year
        )

    return records.order_by("-created_at").first()


# =========================================================
# CLASS PARSER
# =========================================================

def parse_class_number(class_or_course):
    """
    Parse ONLY school classes 1-10.

    Examples:
        1       -> 1
        1st     -> 1
        Class 1 -> 1
        10      -> 10
        10th    -> 10
        Class 10 -> 10

    These return None:
        1st PU
        1st PUC
        2nd PU
        2nd PUC
        Diploma 3rd year
        BE 2nd year
        B.Tech 1st year
        Degree 1st year
    """

    if not class_or_course:
        return None

    val = str(
        class_or_course
    ).lower().strip()

    # -----------------------------------------------------
    # HIGHER / PRE-UNIVERSITY EDUCATION
    # -----------------------------------------------------

    non_school_terms = [
        "puc",
        "p.u.c",
        "pre-university",
        "pre university",
        "diploma",
        "deploma",
        "iti",
        "i.t.i",
        "degree",
        "bca",
        "bsc",
        "b.sc",
        "bcom",
        "b.com",
        "b.a",
        "ba ",
        "btech",
        "b.tech",
        "b.e",
        "be ",
        "undergraduate",
        "college",
        "polytechnic",
        "engineering",
    ]

    if any(
        term in val
        for term in non_school_terms
    ):
        return None

    # -----------------------------------------------------
    # ROMAN NUMERALS
    # -----------------------------------------------------

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

    for roman, number in roman_map.items():

        if val in [
            roman,
            f"class {roman}",
            f"standard {roman}",
            f"std {roman}",
        ]:
            return number

    # -----------------------------------------------------
    # EXACT NUMBER
    # -----------------------------------------------------

    if re.fullmatch(
        r"(10|[1-9])",
        val
    ):
        return int(val)

    # -----------------------------------------------------
    # ORDINAL
    # -----------------------------------------------------

    if re.fullmatch(
        r"(10|[1-9])(st|nd|rd|th)",
        val
    ):
        match = re.match(
            r"(10|[1-9])",
            val
        )

        return int(
            match.group(1)
        )

    # -----------------------------------------------------
    # CLASS / STANDARD / STD + NUMBER
    # -----------------------------------------------------

    match = re.fullmatch(
        r"(class|standard|std)\s*(10|[1-9])",
        val
    )

    if match:
        return int(
            match.group(2)
        )

    # -----------------------------------------------------
    # CLASS / STANDARD / STD + ORDINAL
    # -----------------------------------------------------

    match = re.fullmatch(
        r"(class|standard|std)\s*(10|[1-9])(st|nd|rd|th)",
        val
    )

    if match:
        return int(
            match.group(2)
        )

    return None


def is_class_number(
    class_or_course,
    number
):
    return (
        parse_class_number(
            class_or_course
        )
        == number
    )


def is_school_class(
    class_or_course
):
    return parse_class_number(
        class_or_course
    )


# =========================================================
# COURSE NORMALIZATION
# =========================================================

def normalize_course(value):
    return (
        value or ""
    ).lower().strip()


# =========================================================
# PUC HELPERS
# =========================================================

def is_first_puc(class_or_course):

    if not class_or_course:
        return False

    val = str(
        class_or_course
    ).lower().strip()

    return any(
        term in val
        for term in [
            "1st puc",
            "1st pu",
            "first puc",
            "first pu",
            "puc 1",
            "puc i",
            "class 11",
            "11th",
            "std 11",
        ]
    )


def is_second_puc(class_or_course):

    if not class_or_course:
        return False

    val = str(
        class_or_course
    ).lower().strip()

    return any(
        term in val
        for term in [
            "2nd puc",
            "2nd pu",
            "second puc",
            "second pu",
            "puc 2",
            "puc ii",
            "class 12",
            "12th",
            "std 12",
        ]
    )


def is_puc_course(
    class_or_course
):

    return (
        is_first_puc(
            class_or_course
        )
        or is_second_puc(
            class_or_course
        )
    )


# =========================================================
# OTHER COURSE HELPERS
# =========================================================

def is_diploma_course(
    class_or_course
):

    value = normalize_course(
        class_or_course
    )

    return (
        "diploma" in value
        or "deploma" in value
    )


def is_iti_course(
    class_or_course
):

    value = normalize_course(
        class_or_course
    )

    return "iti" in value


def is_pre_university_course(
    class_or_course
):

    return (
        is_puc_course(
            class_or_course
        )
        or is_diploma_course(
            class_or_course
        )
        or is_iti_course(
            class_or_course
        )
    )


# =========================================================
# DEGREE STUDENT
# =========================================================

def is_degree_student(
    class_or_course
):

    if not class_or_course:
        return False

    val = str(
        class_or_course
    ).lower().strip()

    degree_terms = [
        "degree",
        "bca",
        "bsc",
        "b.sc",
        "bcom",
        "b.com",
        "b.a",
        "ba ",
        "btech",
        "b.tech",
        "b.e",
        "be ",
        "engineering",
        "undergraduate",
        "college",
    ]

    return any(
        term in val
        for term in degree_terms
    )


# =========================================================
# BOOK ELIGIBILITY CLASS CHECK
# =========================================================

def is_book_eligible_class(
    class_or_course
):
    """
    Books are ONLY for Class 1-10.

    Accepted:
        1
        1st
        Class 1
        Standard 1
        10
        10th
        Class 10

    Rejected:
        1st PU
        1st PUC
        2nd PU
        2nd PUC
        PUC
        Diploma
        ITI
        Degree
        BCA
        B.Tech
        BE
    """

    if not class_or_course:
        return False

    value = str(
        class_or_course
    ).strip().lower()

    # -----------------------------------------------------
    # PU / PUC MUST NEVER GET BOOKS
    # -----------------------------------------------------

    pu_terms = [
        "puc",
        "p.u.c",
        "p.u.c.",
        "1st pu",
        "2nd pu",
        "first pu",
        "second pu",
        "1st puc",
        "2nd puc",
        "first puc",
        "second puc",
        "pre university",
        "pre-university",
    ]

    if any(
        term in value
        for term in pu_terms
    ):
        return False

    # -----------------------------------------------------
    # HIGHER EDUCATION MUST NEVER GET BOOKS
    # -----------------------------------------------------

    higher_terms = [
        "diploma",
        "deploma",
        "iti",
        "i.t.i",
        "degree",
        "bca",
        "bsc",
        "b.sc",
        "bcom",
        "b.com",
        "b.a",
        "btech",
        "b.tech",
        "b.e",
        "engineering",
        "polytechnic",
        "college",
        "undergraduate",
    ]

    if any(
        term in value
        for term in higher_terms
    ):
        return False

    # -----------------------------------------------------
    # EXACT SCHOOL CLASS
    # -----------------------------------------------------

    if re.fullmatch(
        r"(10|[1-9])",
        value
    ):
        return True

    # -----------------------------------------------------
    # 1st, 2nd, ... 10th
    # -----------------------------------------------------

    if re.fullmatch(
        r"(10|[1-9])(st|nd|rd|th)",
        value
    ):
        return True

    # -----------------------------------------------------
    # Class 1 / Standard 1 / Std 1
    # -----------------------------------------------------

    if re.fullmatch(
        r"(class|standard|std)\s*(10|[1-9])",
        value
    ):
        return True

    # -----------------------------------------------------
    # Class 1st / Standard 1st
    # -----------------------------------------------------

    if re.fullmatch(
        r"(class|standard|std)\s*(10|[1-9])(st|nd|rd|th)",
        value
    ):
        return True

    return False


# =========================================================
# PERCENTAGE
# =========================================================

def get_percentage(record):

    if record is None:
        return Decimal("0")

    if record.percentage is not None:
        return Decimal(
            str(record.percentage)
        )

    if (
        record.marks_obtained is not None
        and record.total_marks is not None
        and record.total_marks > 0
    ):
        return (
            Decimal(
                str(record.marks_obtained)
            )
            /
            Decimal(
                str(record.total_marks)
            )
        ) * Decimal("100")

    return Decimal("0")


# =========================================================
# CREATE / UPDATE ELIGIBILITY
# =========================================================

def create_or_update_eligibility(
    student,
    benefit_type,
    academic_year,
    eligible,
    selection_rank=None,
    reason="",
):

    record, created = (
        EligibilityRecord.objects
        .update_or_create(
            student=student,
            benefit_type=benefit_type,
            academic_year=academic_year,
            defaults={
                "eligible": eligible,
                "selection_rank": selection_rank,
                "reason": reason,
            },
        )
    )

    return record


# =========================================================
# BOOKS
# =========================================================

def generate_book_eligibility(
    student,
    academic_record
):

    class_value = (
        academic_record.class_or_course
        or ""
    )

    if is_book_eligible_class(
        class_value
    ):

        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.BOOK,
            academic_year=academic_record.academic_year,
            eligible=True,
            selection_rank=None,
            reason=(
                f"Enrolled in school class "
                f"{class_value}. Eligible for "
                f"standard books."
            ),
        )

    # IMPORTANT:
    # Explicitly update old records to FALSE.
    return create_or_update_eligibility(
        student=student,
        benefit_type=BenefitType.BOOK,
        academic_year=academic_record.academic_year,
        eligible=False,
        selection_rank=None,
        reason=(
            f"Not eligible for Books. "
            f"'{class_value}' is not "
            f"School Class 1-10."
        ),
    )


# =========================================================
# WORKBOOK
# =========================================================

def generate_workbook_eligibility(
    student,
    academic_record
):

    if is_class_number(
        academic_record.class_or_course,
        10
    ):

        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.WORKBOOK,
            academic_year=academic_record.academic_year,
            eligible=True,
            reason=(
                "Enrolled in Class 10 "
                "(eligible for board exam "
                "preparation workbooks)."
            ),
        )

    return create_or_update_eligibility(
        student=student,
        benefit_type=BenefitType.WORKBOOK,
        academic_year=academic_record.academic_year,
        eligible=False,
        reason=(
            "Workbook eligibility is "
            "restricted to Class 10."
        ),
    )


# =========================================================
# STUDY KIT - TOP 10 CLASS 10
# =========================================================

def get_top_class_10_students(
    academic_year,
    limit=10
):

    records = (
        AcademicRecord.objects
        .filter(
            academic_year=academic_year
        )
        .select_related("student")
    )

    class_10_records = [
        rec
        for rec in records
        if is_class_number(
            rec.class_or_course,
            10
        )
    ]

    class_10_records.sort(
        key=get_percentage,
        reverse=True
    )

    return class_10_records[:limit]


def generate_study_kit_eligibility(
    academic_year,
    limit=10
):

    top_records = (
        get_top_class_10_students(
            academic_year,
            limit=limit
        )
    )

    count = 0

    for rank, record in enumerate(
        top_records,
        start=1
    ):

        pct = get_percentage(
            record
        )

        create_or_update_eligibility(
            student=record.student,
            benefit_type=BenefitType.STUDY_KIT,
            academic_year=academic_year,
            eligible=True,
            selection_rank=rank,
            reason=(
                f"Top {limit} Merit Scholar "
                f"in Class 10 "
                f"(Rank #{rank} with "
                f"{pct:.2f}% score)."
            ),
        )

        count += 1

    return count


# =========================================================
# STUDY KIT CONTINUATION
# =========================================================

def generate_study_kit_continuation(
    student,
    academic_record
):

    if not is_pre_university_course(
        academic_record.class_or_course
    ):
        return None

    previously_selected = (
        EligibilityRecord.objects
        .filter(
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
            "Student was selected in the "
            "Class 10 Top 10 and continues "
            "to receive Study Kit during "
            "the pre-university course."
        ),
    )


def calculate_study_kit_continuation_batch(
    academic_year
):

    active_students = Student.objects.filter(
        status=Student.Status.ACTIVE
    )

    count = 0

    for student in active_students:

        rec = get_latest_academic_record(
            student,
            academic_year
        )

        if rec:

            result = (
                generate_study_kit_continuation(
                    student,
                    rec
                )
            )

            if result:
                count += 1

    return count


# =========================================================
# LAPTOP QUALIFYING
# =========================================================

def is_final_year_diploma(
    record
):

    value = normalize_course(
        record.class_or_course
    )

    if (
        "diploma" not in value
        and "deploma" not in value
    ):
        return False

    return (
        "3rd year" in value
        or "third year" in value
        or "3rd" in value
        or "third" in value
    )


def get_laptop_qualifying_students(
    academic_year
):

    records = (
        AcademicRecord.objects
        .filter(
            academic_year=academic_year
        )
        .select_related("student")
    )

    qualifying_records = []

    for record in records:

        if is_second_puc(
            record.class_or_course
        ):

            qualifying_records.append(
                record
            )

        elif is_final_year_diploma(
            record
        ):

            qualifying_records.append(
                record
            )

    qualifying_records.sort(
        key=get_percentage,
        reverse=True
    )

    return qualifying_records[:10]


def get_top_puc_students(
    academic_year,
    limit=10
):

    records = AcademicRecord.objects.filter(
        academic_year=academic_year
    )

    puc_records = [
        rec
        for rec in records
        if is_second_puc(
            rec.class_or_course
        )
    ]

    puc_records.sort(
        key=get_percentage,
        reverse=True
    )

    return puc_records[:limit]


def generate_laptop_eligibility(
    academic_year,
    limit=10
):

    top_records = (
        get_laptop_qualifying_students(
            academic_year
        )
    )

    count = 0

    for rank, record in enumerate(
        top_records[:limit],
        start=1
    ):

        pct = get_percentage(
            record
        )

        create_or_update_eligibility(
            student=record.student,
            benefit_type=BenefitType.LAPTOP,
            academic_year=academic_year,
            eligible=True,
            selection_rank=rank,
            reason=(
                f"Top {limit} Merit Laptop "
                f"Scholar in 2nd PUC / Diploma "
                f"Qualifying Stage "
                f"(Rank #{rank} with "
                f"{pct:.2f}% score)."
            ),
        )

        count += 1

    return count


# =========================================================
# LAPTOP DISTRIBUTION
# =========================================================

def is_degree_first_year(
    class_or_course
):

    value = normalize_course(
        class_or_course
    )

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


def is_be_second_year(
    class_or_course
):

    value = normalize_course(
        class_or_course
    )

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
    academic_record
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
        EligibilityRecord.objects
        .filter(
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
            "Previously selected student has "
            "entered the Degree stage and is "
            "eligible to receive the laptop."
        ),
    )


# =========================================================
# INTERNSHIP
#
# RULE:
#
# Current student must be a Degree student
# AND
# student must have been selected for Laptop
# in the PREVIOUS academic year.
# =========================================================

def get_previous_academic_year(
    academic_year
):

    try:

        start_year = int(
            str(academic_year)[:4]
        )

        return (
            f"{start_year - 1}-"
            f"{str(start_year)[-2:]}"
        )

    except (
        ValueError,
        TypeError,
    ):

        return None


def was_selected_for_laptop_previous_year(
    student,
    academic_year
):

    previous_year = (
        get_previous_academic_year(
            academic_year
        )
    )

    if not previous_year:
        return False

    return (
        EligibilityRecord.objects
        .filter(
            student=student,
            benefit_type=BenefitType.LAPTOP,
            academic_year=previous_year,
            eligible=True,
        )
        .exists()
    )


def generate_internship_eligibility(
    student,
    academic_record
):

    current_course = (
        academic_record.class_or_course
        or ""
    )

    # -----------------------------------------------------
    # STEP 1:
    # Must currently be a Degree student.
    # -----------------------------------------------------

    if not is_degree_student(
        current_course
    ):

        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.INTERNSHIP,
            academic_year=academic_record.academic_year,
            eligible=False,
            selection_rank=None,
            reason=(
                f"Not eligible for Internship. "
                f"{current_course} is not a "
                f"Degree program."
            ),
        )

    # -----------------------------------------------------
    # STEP 2:
    # Must have been selected for Laptop
    # in previous academic year.
    # -----------------------------------------------------

    previous_year = (
        get_previous_academic_year(
            academic_record.academic_year
        )
    )

    if not previous_year:

        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.INTERNSHIP,
            academic_year=academic_record.academic_year,
            eligible=False,
            selection_rank=None,
            reason=(
                "Previous academic year "
                "could not be determined."
            ),
        )

    previous_laptop_selected = (
        was_selected_for_laptop_previous_year(
            student,
            academic_record.academic_year
        )
    )

    # -----------------------------------------------------
    # STEP 3:
    # Both conditions satisfied.
    # -----------------------------------------------------

    if previous_laptop_selected:

        return create_or_update_eligibility(
            student=student,
            benefit_type=BenefitType.INTERNSHIP,
            academic_year=academic_record.academic_year,
            eligible=True,
            selection_rank=None,
            reason=(
                f"Degree student who was "
                f"selected for Laptop in "
                f"the previous academic year "
                f"({previous_year}). Eligible "
                f"for Internship."
            ),
        )

    # -----------------------------------------------------
    # STEP 4:
    # Degree student but NO previous laptop.
    # -----------------------------------------------------

    return create_or_update_eligibility(
        student=student,
        benefit_type=BenefitType.INTERNSHIP,
        academic_year=academic_record.academic_year,
        eligible=False,
        selection_rank=None,
        reason=(
            f"Not eligible for Internship. "
            f"Student is a Degree student but "
            f"was not selected for Laptop in "
            f"the previous academic year "
            f"({previous_year})."
        ),
    )


# =========================================================
# SINGLE STUDENT ELIGIBILITY
# =========================================================

def generate_student_eligibility(
    student,
    academic_year
):

    academic_record = (
        get_latest_academic_record(
            student,
            academic_year
        )
    )

    # -----------------------------------------------------
    # NO ACADEMIC RECORD
    # -----------------------------------------------------

    if not academic_record:

        current_cls = (
            student.current_class
            or ""
        )

        results = []

        # Books
        if is_book_eligible_class(
            current_cls
        ):

            b = create_or_update_eligibility(
                student=student,
                benefit_type=BenefitType.BOOK,
                academic_year=academic_year,
                eligible=True,
                reason=(
                    f"Current enrolled class "
                    f"is {current_cls}."
                ),
            )

            results.append(b)

            # Workbook only Class 10
            if is_class_number(
                current_cls,
                10
            ):

                w = create_or_update_eligibility(
                    student=student,
                    benefit_type=BenefitType.WORKBOOK,
                    academic_year=academic_year,
                    eligible=True,
                    reason=(
                        f"Current enrolled class "
                        f"is {current_cls} "
                        f"(Class 10 Workbook)."
                    ),
                )

                results.append(w)

        else:

            create_or_update_eligibility(
                student=student,
                benefit_type=BenefitType.BOOK,
                academic_year=academic_year,
                eligible=False,
                reason=(
                    f"Not eligible for Books. "
                    f"'{current_cls}' is not "
                    f"Class 1-10."
                ),
            )

        # Internship fallback
        if is_degree_student(
            current_cls
        ):

            previous_laptop = (
                was_selected_for_laptop_previous_year(
                    student,
                    academic_year
                )
            )

            internship = create_or_update_eligibility(
                student=student,
                benefit_type=BenefitType.INTERNSHIP,
                academic_year=academic_year,
                eligible=previous_laptop,
                reason=(
                    "Degree student selected "
                    "for Laptop in previous "
                    "academic year."
                    if previous_laptop
                    else
                    "Not eligible: Degree student "
                    "was not selected for Laptop "
                    "in previous academic year."
                ),
            )

            results.append(
                internship
            )

        else:

            internship = create_or_update_eligibility(
                student=student,
                benefit_type=BenefitType.INTERNSHIP,
                academic_year=academic_year,
                eligible=False,
                reason=(
                    "Not a Degree student."
                ),
            )

            results.append(
                internship
            )

        return results

    # -----------------------------------------------------
    # ACADEMIC RECORD EXISTS
    # -----------------------------------------------------

    results = []

    # Books
    book = generate_book_eligibility(
        student,
        academic_record
    )

    if book:
        results.append(book)

    # Workbook
    workbook = generate_workbook_eligibility(
        student,
        academic_record
    )

    if workbook:
        results.append(workbook)

    # Study Kit continuation
    study_kit = (
        generate_study_kit_continuation(
            student,
            academic_record
        )
    )

    if study_kit:
        results.append(study_kit)

    # Laptop distribution
    laptop_distribution = (
        generate_laptop_distribution_eligibility(
            student,
            academic_record
        )
    )

    if laptop_distribution:
        results.append(
            laptop_distribution
        )

    # Internship
    internship = (
        generate_internship_eligibility(
            student,
            academic_record
        )
    )

    if internship:
        results.append(
            internship
        )

    return results


# =========================================================
# 360 PROFILE
# =========================================================

def get_student_eligibility_profile(
    student,
    academic_year=None
):

    academic_record = (
        get_latest_academic_record(
            student,
            academic_year
        )
    )

    effective_class = (
        academic_record.class_or_course
        if academic_record
        else (
            student.current_class
            or "Unknown"
        )
    )

    class_num = parse_class_number(
        effective_class
    )

    pct = (
        float(
            get_percentage(
                academic_record
            )
        )
        if academic_record
        else 0.0
    )

    # Existing DB records
    db_records_qs = (
        EligibilityRecord.objects
        .filter(
            student=student
        )
    )

    if academic_year:

        db_records_qs = (
            db_records_qs.filter(
                academic_year=academic_year
            )
        )

    db_records = {
        r.benefit_type: r
        for r in db_records_qs
    }

    benefits_eval = []

    # =====================================================
    # 1. BOOKS
    # =====================================================

    book_rec = db_records.get(
        BenefitType.BOOK
    )

    book_auto = (
        is_book_eligible_class(
            effective_class
        )
    )

    benefits_eval.append({
        "benefit_type": BenefitType.BOOK,
        "benefit_display": "Books (Class 1-10)",
        "icon": "📚",

        "is_eligible": (
            book_auto
            and (
                book_rec.eligible
                if book_rec
                else True
            )
        ),

        "record_exists": (
            book_rec is not None
        ),

        "selection_rank": (
            book_rec.selection_rank
            if book_rec
            else None
        ),

        "reason": (
            book_rec.reason
            if book_rec
            else (
                "Eligible: Enrolled in "
                "school Class 1-10"
                if book_auto
                else
                "Ineligible: Not in "
                "school Class 1-10"
            )
        ),

        "rule_summary": (
            "Standard textbook package "
            "for school students in "
            "Class 1-10 only."
        ),
    })

    # =====================================================
    # 2. WORKBOOK
    # =====================================================

    wb_rec = db_records.get(
        BenefitType.WORKBOOK
    )

    wb_auto = (
        class_num == 10
    )

    benefits_eval.append({
        "benefit_type": BenefitType.WORKBOOK,
        "benefit_display": "Workbook (Class 10)",
        "icon": "📝",

        "is_eligible": (
            wb_rec.eligible
            if wb_rec
            else wb_auto
        ),

        "record_exists": (
            wb_rec is not None
        ),

        "selection_rank": (
            wb_rec.selection_rank
            if wb_rec
            else None
        ),

        "reason": (
            wb_rec.reason
            if wb_rec
            else (
                "Eligible: Enrolled in "
                "Class 10 Board preparation"
                if wb_auto
                else
                "Ineligible: Available only "
                "for Class 10"
            )
        ),

        "rule_summary": (
            "Intensive revision and STEM "
            "practice workbook for Class 10."
        ),
    })

    # =====================================================
    # 3. STUDY KIT
    # =====================================================

    sk_rec = db_records.get(
        BenefitType.STUDY_KIT
    )

    is_puc = (
        is_first_puc(
            effective_class
        )
        or
        is_second_puc(
            effective_class
        )
    )

    prev_sk = (
        EligibilityRecord.objects
        .filter(
            student=student,
            benefit_type=BenefitType.STUDY_KIT,
            eligible=True
        )
        .exclude(
            academic_year=academic_year
        )
        .exists()
    )

    sk_auto = (
        class_num == 10
        and pct >= 80.0
    ) or (
        is_puc
        and prev_sk
    )

    benefits_eval.append({
        "benefit_type": BenefitType.STUDY_KIT,
        "benefit_display": (
            "Study Kit "
            "(Merit & PUC Continuation)"
        ),
        "icon": "🎒",

        "is_eligible": (
            sk_rec.eligible
            if sk_rec
            else sk_auto
        ),

        "record_exists": (
            sk_rec is not None
        ),

        "selection_rank": (
            sk_rec.selection_rank
            if sk_rec
            else None
        ),

        "reason": (
            sk_rec.reason
            if sk_rec
            else (
                "Eligible based on "
                "Class 10 merit or "
                "PUC continuation."
                if sk_auto
                else
                "Requires Top 10 Class 10 "
                "selection or PUC continuation."
            )
        ),

        "rule_summary": (
            "Awarded to Top 10 Class 10 "
            "rank holders and continued "
            "through PUC."
        ),
    })

    # =====================================================
    # 4. LAPTOP
    # =====================================================

    lp_rec = db_records.get(
        BenefitType.LAPTOP
    )

    lp_auto = (
        is_second_puc(
            effective_class
        )
        and pct >= 85.0
    )

    benefits_eval.append({
        "benefit_type": BenefitType.LAPTOP,
        "benefit_display": (
            "Laptop Scholarship "
            "(Top 10 2nd PUC)"
        ),
        "icon": "💻",

        "is_eligible": (
            lp_rec.eligible
            if lp_rec
            else lp_auto
        ),

        "record_exists": (
            lp_rec is not None
        ),

        "selection_rank": (
            lp_rec.selection_rank
            if lp_rec
            else None
        ),

        "reason": (
            lp_rec.reason
            if lp_rec
            else (
                "High merit 2nd PUC "
                "scholar eligible for "
                "laptop grant"
                if lp_auto
                else
                "Requires Top 10 merit "
                "selection in 2nd PUC."
            )
        ),

        "rule_summary": (
            "Top 10 qualifying students "
            "from 2nd PUC / Diploma."
        ),
    })

    # =====================================================
    # 5. INTERNSHIP
    # =====================================================

    in_rec = db_records.get(
        BenefitType.INTERNSHIP
    )

    # IMPORTANT:
    # Internship is NOT automatically given
    # just because the student is a Degree student.

    internship_auto = False

    if academic_record:

        if is_degree_student(
            effective_class
        ):

            internship_auto = (
                was_selected_for_laptop_previous_year(
                    student,
                    academic_record.academic_year
                )
            )

    benefits_eval.append({
        "benefit_type": BenefitType.INTERNSHIP,
        "benefit_display": (
            "Internship "
            "(Degree + Previous Laptop)"
        ),
        "icon": "💼",

        "is_eligible": (
            internship_auto
            and (
                in_rec.eligible
                if in_rec
                else True
            )
        ),

        "record_exists": (
            in_rec is not None
        ),

        "selection_rank": (
            in_rec.selection_rank
            if in_rec
            else None
        ),

        "reason": (
            in_rec.reason
            if in_rec
            else (
                "Eligible: Degree student "
                "who was selected for Laptop "
                "in the previous academic year."
                if internship_auto
                else
                "Ineligible: Student must be "
                "a Degree student AND must have "
                "been selected for Laptop in "
                "the previous academic year."
            )
        ),

        "rule_summary": (
            "Internship is available only "
            "to Degree students who were "
            "selected for a Laptop in the "
            "previous academic year."
        ),
    })

    return {
        "student_id": student.id,

        "student_name": (
            student.student_name
        ),

        "admission_number": (
            student.admission_number
        ),

        "school_name": (
            student.school.name
            if student.school
            else "General"
        ),

        "current_class": (
            effective_class
        ),

        "percentage": pct,

        "academic_year": (
            academic_year
            or (
                academic_record.academic_year
                if academic_record
                else "2026-27"
            )
        ),

        "benefits": benefits_eval,
    }


# =========================================================
# GENERATE ALL ELIGIBILITY
# =========================================================

def generate_all_eligibility(
    academic_year,
    target_benefits=None
):

    students = Student.objects.filter(
        status=Student.Status.ACTIVE
    )

    do_all = (
        not target_benefits
        or "ALL" in target_benefits
    )

    do_books = (
        do_all
        or BenefitType.BOOK
        in target_benefits
    )

    do_workbooks = (
        do_all
        or BenefitType.WORKBOOK
        in target_benefits
    )

    do_study_kit = (
        do_all
        or BenefitType.STUDY_KIT
        in target_benefits
    )

    do_laptops = (
        do_all
        or BenefitType.LAPTOP
        in target_benefits
    )

    do_internships = (
        do_all
        or BenefitType.INTERNSHIP
        in target_benefits
    )

    processed_students = 0
    books_count = 0
    workbooks_count = 0
    study_kit_cont_count = 0
    internships_count = 0

    # =====================================================
    # PROCESS STUDENTS
    # =====================================================

    for student in students:

        processed_students += 1

        rec = get_latest_academic_record(
            student,
            academic_year
        )

        # =================================================
        # BOOKS
        # =================================================

        if do_books:

            if rec:

                b = generate_book_eligibility(
                    student,
                    rec
                )

                if b and b.eligible:
                    books_count += 1

            else:

                class_value = (
                    student.current_class
                    or ""
                )

                if is_book_eligible_class(
                    class_value
                ):

                    create_or_update_eligibility(
                        student=student,
                        benefit_type=BenefitType.BOOK,
                        academic_year=academic_year,
                        eligible=True,
                        reason=(
                            f"Current enrolled "
                            f"class is {class_value}."
                        ),
                    )

                    books_count += 1

                else:

                    # IMPORTANT:
                    # Remove stale Books eligibility.

                    create_or_update_eligibility(
                        student=student,
                        benefit_type=BenefitType.BOOK,
                        academic_year=academic_year,
                        eligible=False,
                        selection_rank=None,
                        reason=(
                            f"Not eligible for Books. "
                            f"'{class_value}' is not "
                            f"School Class 1-10."
                        ),
                    )

        # =================================================
        # WORKBOOK
        # =================================================

        if do_workbooks:

            if rec:

                w = generate_workbook_eligibility(
                    student,
                    rec
                )

                if w and w.eligible:
                    workbooks_count += 1

            else:

                if is_class_number(
                    student.current_class,
                    10
                ):

                    create_or_update_eligibility(
                        student=student,
                        benefit_type=BenefitType.WORKBOOK,
                        academic_year=academic_year,
                        eligible=True,
                        reason=(
                            f"Current enrolled "
                            f"class is "
                            f"{student.current_class} "
                            f"(Class 10 Workbook)."
                        ),
                    )

                    workbooks_count += 1

                else:

                    create_or_update_eligibility(
                        student=student,
                        benefit_type=BenefitType.WORKBOOK,
                        academic_year=academic_year,
                        eligible=False,
                        reason=(
                            "Workbook eligibility "
                            "is restricted to "
                            "Class 10."
                        ),
                    )

        # =================================================
        # STUDY KIT CONTINUATION
        # =================================================

        if do_study_kit:

            if rec:

                sk = (
                    generate_study_kit_continuation(
                        student,
                        rec
                    )
                )

                if sk and sk.eligible:
                    study_kit_cont_count += 1

        # =================================================
        # INTERNSHIP
        # =================================================

        if do_internships:

            if rec:

                internship_result = (
                    generate_internship_eligibility(
                        student,
                        rec
                    )
                )

                if (
                    internship_result
                    and internship_result.eligible
                ):
                    internships_count += 1

            else:

                current_course = (
                    student.current_class
                    or ""
                )

                if is_degree_student(
                    current_course
                ):

                    previous_laptop = (
                        was_selected_for_laptop_previous_year(
                            student,
                            academic_year
                        )
                    )

                    internship_result = (
                        create_or_update_eligibility(
                            student=student,
                            benefit_type=BenefitType.INTERNSHIP,
                            academic_year=academic_year,
                            eligible=previous_laptop,
                            selection_rank=None,
                            reason=(
                                "Degree student who "
                                "was selected for "
                                "Laptop in previous "
                                "academic year."
                                if previous_laptop
                                else
                                "Not eligible: Degree "
                                "student was not "
                                "selected for Laptop "
                                "in previous "
                                "academic year."
                            ),
                        )
                    )

                    if internship_result.eligible:
                        internships_count += 1

                else:

                    create_or_update_eligibility(
                        student=student,
                        benefit_type=BenefitType.INTERNSHIP,
                        academic_year=academic_year,
                        eligible=False,
                        selection_rank=None,
                        reason=(
                            "Not a Degree student."
                        ),
                    )

    # =====================================================
    # TOP 10 CLASS 10 → STUDY KIT
    # =====================================================

    study_kit_top_count = 0

    if do_study_kit:

        study_kit_top_count = (
            generate_study_kit_eligibility(
                academic_year
            )
        )

    # =====================================================
    # TOP 10 2ND PUC / DIPLOMA → LAPTOP
    # =====================================================

    laptop_count = 0

    if do_laptops:

        laptop_count = (
            generate_laptop_eligibility(
                academic_year
            )
        )

    # =====================================================
    # TOTAL
    # =====================================================

    total_eligible = (
        EligibilityRecord.objects
        .filter(
            academic_year=academic_year,
            eligible=True,
        )
        .count()
    )

    return {
        "academic_year": academic_year,
        "processed_students": processed_students,
        "books_count": books_count,
        "workbooks_count": workbooks_count,
        "study_kit_top_count": study_kit_top_count,
        "study_kit_continuation_count": (
            study_kit_cont_count
        ),
        "study_kit_total": (
            study_kit_top_count
            + study_kit_cont_count
        ),
        "laptop_count": laptop_count,
        "internships_count": (
            internships_count
        ),
        "total_eligible_records": (
            total_eligible
        ),
    }


# =========================================================
# ALIASES
# =========================================================

def calculate_student_eligibility(
    student,
    academic_year
):
    return generate_student_eligibility(
        student,
        academic_year
    )


def calculate_study_kit_eligibility(
    academic_year,
    limit=10
):
    return generate_study_kit_eligibility(
        academic_year,
        limit=limit
    )


def calculate_study_kit_continuation(
    academic_year
):
    return calculate_study_kit_continuation_batch(
        academic_year
    )


def calculate_laptop_eligibility(
    academic_year,
    limit=10
):
    return generate_laptop_eligibility(
        academic_year,
        limit=limit
    )


def run_legacy_generate_all_eligibility(
    academic_year
):
    return generate_all_eligibility(
        academic_year
    )