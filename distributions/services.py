from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from students.models import Student
from schools.models import School, SchoolResource
from academics.models import AcademicRecord
from eligibility.services import get_percentage
from inventory.models import InventoryItem, Laptop, LaptopAssignment
from inventory.services import process_stock_out, issue_laptop
from .models import Distribution, BenefitType, RecipientType, SchoolEssentialType, StudyKit


def is_student_class_1_to_10(current_class):
    """Check if class is between Class 1 and Class 10"""
    if not current_class:
        return False
    cls_str = str(current_class).lower()
    for i in range(1, 11):
        if f"class {i}" in cls_str or f"grade {i}" in cls_str or f"std {i}" in cls_str or cls_str == str(i):
            return True
    return False


def is_student_class_10(current_class):
    """Check if student is in Class 10"""
    if not current_class:
        return False
    cls_str = str(current_class).lower()
    return "10" in cls_str or "x" in cls_str.split() or "tenth" in cls_str


def is_student_up_to_2nd_puc(current_class):
    """Check if student is enrolled from Class 1 up to 2nd PUC"""
    if not current_class:
        return True
    cls_str = str(current_class).lower()
    # Class 1 to 10
    if is_student_class_1_to_10(current_class):
        return True
    # PUC
    if "puc" in cls_str or "11" in cls_str or "12" in cls_str or "1st puc" in cls_str or "2nd puc" in cls_str or "plus two" in cls_str or "intermediate" in cls_str:
        return True
    return True


def get_eligible_students_for_benefit(benefit_type, academic_year=None):
    """
    Return ONLY students who are eligible for the selected benefit.

    Distribution dropdown uses this function, so an ineligible student
    must never appear as a selectable recipient.
    """
    from eligibility.models import EligibilityRecord

    benefit_type = str(benefit_type or "").upper().strip()

    students = Student.objects.select_related("school").filter(
        status=Student.Status.ACTIVE
    )

    # Books and Workbooks can be determined directly from the student's
    # current academic class.
    if benefit_type == BenefitType.BOOK:
        return [
            s for s in students
            if is_student_class_1_to_10(s.current_class)
        ]

    if benefit_type == BenefitType.WORKBOOK:
        return [
            s for s in students
            if is_student_class_10(s.current_class)
        ]

    # Study Kit and Laptop MUST use the eligibility records.
    # This allows the eligibility module to handle:
    #
    #   Class 10 Top 10
    #   -> 2-year Study Kit continuation
    #   -> PUC / Diploma / other course progression
    #   -> Overall Top 10 laptop selection
    #   -> Laptop distribution stage
    #   -> Degree Study Kit continuation
    #
    # without Distribution having to duplicate those rules.
    if benefit_type in (
        BenefitType.STUDY_KIT,
        BenefitType.LAPTOP,
    ):
        qs = EligibilityRecord.objects.filter(
            benefit_type=benefit_type,
            eligible=True,
            student__status=Student.Status.ACTIVE,
        )

        if academic_year:
            qs = qs.filter(academic_year=academic_year)

        student_ids = qs.values_list(
            "student_id",
            flat=True,
        ).distinct()

        return list(
            students.filter(
                id__in=student_ids
            ).order_by("student_name")
        )

    # Internship and any future benefit types can also use
    # EligibilityRecord when records exist.
    qs = EligibilityRecord.objects.filter(
        benefit_type=benefit_type,
        eligible=True,
        student__status=Student.Status.ACTIVE,
    )

    if academic_year:
        qs = qs.filter(academic_year=academic_year)

    student_ids = qs.values_list(
        "student_id",
        flat=True,
    ).distinct()

    return list(
        students.filter(
            id__in=student_ids
        ).order_by("student_name")
    )

def get_top_puc_students(academic_year=None, limit=10):
    """
    Fetch Top 10 PUC students ranked by academic performance (percentage & rank)
    for merit-based Laptop scholarship distribution.
    """
    records = AcademicRecord.objects.select_related("student", "student__school").filter(
        Q(class_or_course__icontains="PUC") |
        Q(class_or_course__icontains="12") |
        Q(student__current_class__icontains="PUC")
    )

    if academic_year:
        records = records.filter(academic_year=academic_year)

    # Order by highest percentage, best rank
    records = records.order_by("-percentage", "rank", "student__student_name")

    top_students = []
    seen_student_ids = set()

    for rec in records:
        if not rec.student or rec.student.id in seen_student_ids:
            continue
        seen_student_ids.add(rec.student.id)

        # Check if student already has a laptop assigned
        has_laptop = LaptopAssignment.objects.filter(
            student=rec.student,
            status=LaptopAssignment.Status.ISSUED,
        ).exists()

        active_assignment = LaptopAssignment.objects.filter(
            student=rec.student,
            status=LaptopAssignment.Status.ISSUED,
        ).first()

        top_students.append({
            "rank_position": len(top_students) + 1,
            "student_id": rec.student.id,
            "student_name": rec.student.student_name,
            "admission_number": rec.student.admission_number,
            "current_class": rec.class_or_course or rec.student.current_class,
            "school_name": rec.student.school.name if rec.student.school else "General",
            "academic_year": rec.academic_year,
            "percentage": float(get_percentage(rec)),
            "class_rank": rec.rank or (len(top_students) + 1),
            "promotion_status": rec.promotion_status or "Promoted",
            "has_laptop": has_laptop,
            "assigned_laptop": active_assignment.laptop.asset_number if active_assignment else None,
        })

        if len(top_students) >= limit:
            break

    return top_students


@transaction.atomic
def distribute_books(student, item, quantity=1, academic_year="2026-27", issued_by="", remarks=""):
    """
    Distribute Books to an eligible student (Class 1â€“10).
    Automatically deducts Inventory stock and logs immutable distribution and stock records.
    """
    if quantity <= 0:
        raise ValidationError("Distribution quantity must be greater than zero.")

    if not is_student_class_1_to_10(student.current_class):
        raise ValidationError(
            f"Student {student.student_name} is in '{student.current_class}'. "
            "Book distribution is eligible for Class 1 to Class 10 students only."
        )

    # Process inventory stock out
    stock_dest = f"Student: {student.student_name} ({student.current_class}) - {student.school.name if student.school else ''}"
    ref_no = f"DIST-BK-{student.admission_number}"
    process_stock_out(
        item=item,
        quantity=quantity,
        source_destination=stock_dest,
        reference_number=ref_no,
        performed_by=issued_by,
        notes=f"Book distribution: {remarks}" if remarks else "Book distribution",
    )

    distribution = Distribution.objects.create(
        benefit_type=BenefitType.BOOK,
        recipient_type=RecipientType.STUDENT,
        student=student,
        school=student.school,
        inventory_item=item,
        academic_year=academic_year,
        quantity=quantity,
        issued_by=issued_by,
        remarks=remarks,
        distribution_date=timezone.localdate(),
    )

    return distribution


@transaction.atomic
def distribute_workbooks(student, item, quantity=1, academic_year="2026-27", issued_by="", remarks=""):
    """
    Distribute Workbooks to eligible Class 10 students.
    Automatically deducts Inventory stock and logs distribution.
    """
    if quantity <= 0:
        raise ValidationError("Distribution quantity must be greater than zero.")

    if not is_student_class_10(student.current_class):
        raise ValidationError(
            f"Student {student.student_name} is in '{student.current_class}'. "
            "Workbook distribution is strictly for Class 10 students."
        )

    stock_dest = f"Class 10 Student: {student.student_name} ({student.school.name if student.school else ''})"
    ref_no = f"DIST-WB-{student.admission_number}"
    process_stock_out(
        item=item,
        quantity=quantity,
        source_destination=stock_dest,
        reference_number=ref_no,
        performed_by=issued_by,
        notes=f"Class 10 Workbook distribution: {remarks}" if remarks else "Class 10 Workbook distribution",
    )

    distribution = Distribution.objects.create(
        benefit_type=BenefitType.WORKBOOK,
        recipient_type=RecipientType.STUDENT,
        student=student,
        school=student.school,
        inventory_item=item,
        academic_year=academic_year,
        quantity=quantity,
        issued_by=issued_by,
        remarks=remarks,
        distribution_date=timezone.localdate(),
    )

    return distribution


@transaction.atomic
def issue_study_kit(student, item=None, kit=None, quantity=1, academic_year="2026-27", issued_by="", remarks=""):
    """
    Issue Study Kit to students continuing from Class 1 up to 2nd PUC.
    Deducts inventory stock and records distribution.
    """
    if quantity <= 0:
        raise ValidationError("Study kit quantity must be greater than zero.")

    if not is_student_up_to_2nd_puc(student.current_class):
        raise ValidationError(
            f"Student {student.student_name} ({student.current_class}) is not within the eligible grade range (Class 1 to 2nd PUC)."
        )

    if item:
        stock_dest = f"Student Study Kit: {student.student_name} ({student.current_class} - {student.school.name if student.school else ''})"
        ref_no = f"DIST-SK-{student.admission_number}"
        process_stock_out(
            item=item,
            quantity=quantity,
            source_destination=stock_dest,
            reference_number=ref_no,
            performed_by=issued_by,
            notes=f"Study kit issuance: {remarks}" if remarks else "Study kit issuance",
        )

    distribution = Distribution.objects.create(
        benefit_type=BenefitType.STUDY_KIT,
        recipient_type=RecipientType.STUDENT,
        student=student,
        school=student.school,
        inventory_item=item,
        study_kit=kit,
        academic_year=academic_year,
        quantity=quantity,
        issued_by=issued_by,
        remarks=remarks,
        distribution_date=timezone.localdate(),
    )

    return distribution


@transaction.atomic
def issue_laptop_scholarship(student, laptop, academic_year="2026-27", notes="", issued_by=""):
    """
    Issue laptop to student (e.g. Top 10 PUC merit scholarship or eligible beneficiary).
    Updates laptop status to ISSUED, records LaptopAssignment, and creates Distribution record.
    """
    assignment = issue_laptop(
        student=student,
        laptop=laptop,
        academic_year=academic_year,
        issue_notes=notes,
        bypass_eligibility=True,
    )

    distribution = Distribution.objects.create(
        benefit_type=BenefitType.LAPTOP,
        recipient_type=RecipientType.STUDENT,
        student=student,
        school=student.school,
        academic_year=academic_year,
        quantity=1,
        issued_by=issued_by,
        remarks=f"Laptop Asset #{laptop.asset_number} ({laptop.brand} {laptop.model_name}). {notes}",
        distribution_date=timezone.localdate(),
    )

    return assignment, distribution


@transaction.atomic
def distribute_school_essentials(school, item, essential_type, quantity, academic_year="2026-27", issued_by="", remarks=""):
    """
    Distribute Government School Essentials (Benches, Desks, Chairs, Whiteboards, Library Books,
    Lab Gear, Water Filters, Fans, Sports Kits, Projectors, etc.).
    Automatically deducts physical inventory and updates SchoolResource on School.
    """
    if quantity <= 0:
        raise ValidationError("Essential distribution quantity must be greater than zero.")

    # Process inventory deduction
    stock_dest = f"Govt School: {school.name} (UDISE: {school.udise_code})"
    ref_no = f"DIST-SCH-{school.udise_code}"
    process_stock_out(
        item=item,
        quantity=quantity,
        source_destination=stock_dest,
        reference_number=ref_no,
        performed_by=issued_by,
        notes=f"Government School Essential ({essential_type}): {remarks}" if remarks else f"School essential distribution ({essential_type})",
    )

    distribution = Distribution.objects.create(
        benefit_type=BenefitType.SCHOOL_ESSENTIAL,
        recipient_type=RecipientType.SCHOOL,
        school=school,
        inventory_item=item,
        essential_item_type=essential_type,
        academic_year=academic_year,
        quantity=quantity,
        issued_by=issued_by,
        remarks=remarks,
        distribution_date=timezone.localdate(),
    )

    # Cross-portal synchronization: Update/create SchoolResource for the school
    resource_name = item.item_name
    existing_res = SchoolResource.objects.filter(school=school, resource_name__iexact=resource_name).first()
    if existing_res:
        existing_res.quantity += quantity
        existing_res.status = "Delivered"
        existing_res.last_updated_note = f"Dispatched +{quantity} on {timezone.localdate().strftime('%Y-%m-%d')}"
        existing_res.save()
    else:
        SchoolResource.objects.create(
            school=school,
            resource_name=resource_name,
            quantity=quantity,
            status="Delivered",
            last_updated_note=f"Dispatched +{quantity} on {timezone.localdate().strftime('%Y-%m-%d')}",
            details=f"Essential category: {essential_type}. {remarks}",
        )

    return distribution
