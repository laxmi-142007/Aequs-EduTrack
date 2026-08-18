import datetime
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg

from .models import InternshipProgram, InternshipPlacement, InternshipMilestone, Department
from students.models import Student
from schools.models import School
from eligibility.models import EligibilityRecord, BenefitType


def is_internship_eligible_class(class_or_course):
    """
    Returns True ONLY for Degree, Engineering, Polytechnic, Diploma, ITI,
    or Undergraduate candidates.
    Strictly excludes Class 1-10 school students and 1st/2nd PUC students
    (since PUC students receive Study Kits & Laptop Scholarships instead).
    """
    if not class_or_course:
        return False
    val = str(class_or_course).lower().strip()
    
    # Reject school students (Class 1 through 10)
    for i in range(1, 11):
        if val == f"class {i}" or val.startswith(f"class {i} ") or val == f"{i}th" or val.startswith(f"std {i}"):
            return False

    # Reject 1st & 2nd PUC / Intermediate / 11th & 12th
    if any(puc in val for puc in ["puc", "1st puc", "2nd puc", "pu college", "plus two", "intermediate", "11th", "12th", "class 11", "class 12"]):
        return False

    return any(term in val for term in [
        "degree", "diploma", "polytechnic", "iti",
        "b.e", "be", "b.tech", "btech", "b.sc", "bsc", "bca", "b.com", "bcom",
        "b.a", "ba", "m.tech", "mca", "undergraduate", "vocational", "engineering"
    ])


def get_internship_kpis(academic_year=None):
    """
    Computes dashboard KPI metrics for internships.
    """
    qs = InternshipPlacement.objects.all()
    if academic_year:
        qs = qs.filter(academic_year=academic_year)

    total_interns = qs.count()
    active_interns = qs.filter(
        status__in=[
            InternshipPlacement.Status.SELECTED,
            InternshipPlacement.Status.IN_PROGRESS,
        ]
    ).count()
    completed_interns = qs.filter(
        status=InternshipPlacement.Status.COMPLETED
    ).count()
    certificates_issued = qs.filter(
        certificate_issued=True
    ).count()

    total_programs = InternshipProgram.objects.count()
    open_programs = InternshipProgram.objects.filter(
        status=InternshipProgram.Status.OPEN
    ).count()

    total_stipend = qs.aggregate(
        total=Sum("stipend_amount")
    )["total"] or Decimal("0.00")

    avg_attendance = qs.aggregate(
        avg=Avg("attendance_percentage")
    )["avg"] or Decimal("0.00")

    dept_counts = (
        qs.values("department")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    dept_map = dict(Department.choices)
    dept_stats = [
        {
            "department": d["department"],
            "label": dept_map.get(d["department"], d["department"]),
            "count": d["count"],
        }
        for d in dept_counts
    ]

    status_counts = (
        qs.values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    status_map = dict(InternshipPlacement.Status.choices)
    status_stats = [
        {
            "status": s["status"],
            "label": status_map.get(s["status"], s["status"]),
            "count": s["count"],
        }
        for s in status_counts
    ]

    return {
        "total_interns": total_interns,
        "active_interns": active_interns,
        "completed_interns": completed_interns,
        "certificates_issued": certificates_issued,
        "total_programs": total_programs,
        "open_programs": open_programs,
        "total_stipend": float(total_stipend),
        "avg_attendance": round(float(avg_attendance), 1),
        "dept_stats": dept_stats,
        "status_stats": status_stats,
    }


def generate_certificate_number(placement):
    """
    Generates a unique formal certificate identifier.
    e.g. AEQ-CERT-2026-00042
    """
    year = placement.start_date.year if placement.start_date else timezone.now().year
    return f"AEQ-CERT-{year}-{placement.id:05d}"


def get_eligible_students_for_internship(academic_year="2026-27"):
    """
    Fetches students marked eligible for BenefitType.INTERNSHIP or degree/diploma/PUC scholars.
    """
    # 1. From eligibility records
    eligible_student_ids = list(
        EligibilityRecord.objects.filter(
            benefit_type=BenefitType.INTERNSHIP,
            eligible=True,
        ).values_list("student_id", flat=True)
    )

    placed_student_ids = set(
        InternshipPlacement.objects.values_list("student_id", flat=True)
    )

    candidates = []
    seen_ids = set()
    
    # Students with explicit eligibility record
    students_with_eligibility = Student.objects.filter(
        id__in=eligible_student_ids
    ).select_related("school")

    for s in students_with_eligibility:
        if is_internship_eligible_class(s.current_class):
            seen_ids.add(s.id)
            candidates.append({
                "id": s.id,
                "name": s.student_name,
                "admission_number": s.admission_number,
                "school_id": s.school.id if s.school else None,
                "school_name": s.school.name if s.school else "General",
                "current_class": s.current_class,
                "is_placed": s.id in placed_student_ids,
                "source": "Eligibility Engine (Degree / Higher Ed Track)",
                "phone": s.student_phone or s.parent_phone or "",
                "email": s.email or "",
            })

    # Add other PUC / Degree / Diploma scholars in the system
    other_students = Student.objects.exclude(
        id__in=seen_ids
    ).select_related("school")

    for s in other_students:
        if is_internship_eligible_class(s.current_class):
            seen_ids.add(s.id)
            candidates.append({
                "id": s.id,
                "name": s.student_name,
                "admission_number": s.admission_number,
                "school_id": s.school.id if s.school else None,
                "school_name": s.school.name if s.school else "General",
                "current_class": s.current_class,
                "is_placed": s.id in placed_student_ids,
                "source": "Higher Education Scholar Pool",
                "phone": s.student_phone or s.parent_phone or "",
                "email": s.email or "",
            })

    return candidates


def seed_internship_demo_data():
    """
    Populates sample corporate programs and higher-education scholar placements.
    """
    today = timezone.localdate()
    start_cur = today - datetime.timedelta(days=45)
    end_cur = start_cur + datetime.timedelta(days=90)
    
    start_comp = today - datetime.timedelta(days=120)
    end_comp = today - datetime.timedelta(days=30)

    # 1. Create Core Internship Programs
    programs_data = [
        {
            "title": "Aequs Aerospace CNC & Precision Engineering Track",
            "program_code": "AEQ-INT-2026-AERO",
            "company_name": "Aequs Aerospace SEZ",
            "department": Department.PRECISION_MANUFACTURING,
            "location": "Belagavi Special Economic Zone, Unit 1",
            "duration_months": 3,
            "stipend_amount": Decimal("10000.00"),
            "total_slots": 20,
            "academic_year": "2026-27",
            "start_date": start_cur,
            "end_date": end_cur,
            "mentor_in_charge": "Rajesh Kulkarni (Senior Lead Engineer)",
            "mentor_contact": "rajesh.kulkarni@aequs.com",
            "eligibility_criteria": "Degree / Diploma in Mechanical / Production Engineering with >= 65% aggregate.",
            "description": "Comprehensive practical industrial training on 5-Axis CNC machining, GD&T blueprint analysis, precision aerospace milling, and CMM quality inspections.",
            "status": InternshipProgram.Status.IN_PROGRESS,
        },
        {
            "title": "Quality Assurance & Aerospace Metrology Track",
            "program_code": "AEQ-INT-2026-QA",
            "company_name": "Aequs Aerospace Systems",
            "department": Department.QUALITY_ASSURANCE,
            "location": "Belagavi SEZ, QC Testing Facility",
            "duration_months": 3,
            "stipend_amount": Decimal("9000.00"),
            "total_slots": 15,
            "academic_year": "2026-27",
            "start_date": start_cur,
            "end_date": end_cur,
            "mentor_in_charge": "Deepa Patil (QA Lead Specialist)",
            "mentor_contact": "deepa.patil@aequs.com",
            "eligibility_criteria": "B.Sc / Diploma / Degree in Mechanical, Electronics, or Industrial Physics.",
            "description": "Hands-on calibration, coordinate measuring machines (CMM), surface roughness profiling, and AS9100 quality compliance documentation.",
            "status": InternshipProgram.Status.IN_PROGRESS,
        },
        {
            "title": "Industrial IoT & Smart Factory IT Operations",
            "program_code": "AEQ-INT-2026-IT",
            "company_name": "Aequs Digital & Technology Division",
            "department": Department.IT_AND_SOFTWARE,
            "location": "Aequs Tech Park, Belagavi",
            "duration_months": 4,
            "stipend_amount": Decimal("12000.00"),
            "total_slots": 12,
            "academic_year": "2026-27",
            "start_date": today + datetime.timedelta(days=15),
            "end_date": today + datetime.timedelta(days=135),
            "mentor_in_charge": "Sanjay Deshmukh (Digital Solutions Architect)",
            "mentor_contact": "sanjay.deshmukh@aequs.com",
            "eligibility_criteria": "B.E. Computer Science / BCA / IT Diploma students with knowledge of Python & SQL.",
            "description": "Smart sensor telemetry, factory floor MES integration, real-time dashboarding, and shopfloor predictive maintenance pipelines.",
            "status": InternshipProgram.Status.OPEN,
        },
        {
            "title": "Supply Chain & Aerospace Logistics Track",
            "program_code": "AEQ-INT-2026-SCM",
            "company_name": "Aequs Consumer & Aerospace Logistics",
            "department": Department.SUPPLY_CHAIN,
            "location": "Aequs Logistics Hub, Hubballi",
            "duration_months": 3,
            "stipend_amount": Decimal("8500.00"),
            "total_slots": 10,
            "academic_year": "2026-27",
            "start_date": start_comp,
            "end_date": end_comp,
            "mentor_in_charge": "Priyanka Naik (Logistics Operations Manager)",
            "mentor_contact": "priyanka.naik@aequs.com",
            "eligibility_criteria": "B.Com / BBA / Logistics Diploma scholars with good analytical skills.",
            "description": "Raw material procurement workflows, ERP SAP inventory tracking, export documentation, and customs compliance for SEZ operations.",
            "status": InternshipProgram.Status.COMPLETED,
        },
        {
            "title": "Tool & Die Design & Additive Prototyping",
            "program_code": "AEQ-INT-2026-TOOL",
            "company_name": "Aequs Tooling Division",
            "department": Department.TOOL_AND_DIE,
            "location": "Belagavi Tooling Center",
            "duration_months": 6,
            "stipend_amount": Decimal("11000.00"),
            "total_slots": 10,
            "academic_year": "2026-27",
            "start_date": today + datetime.timedelta(days=30),
            "end_date": today + datetime.timedelta(days=210),
            "mentor_in_charge": "Mahesh Bhat (Senior Tooling Consultant)",
            "mentor_contact": "mahesh.bhat@aequs.com",
            "eligibility_criteria": "Tool & Die Diploma or NTTF / GTTC certified candidates.",
            "description": "Injection molding tool design, press tools, NX CAD/CAM surfacing, and rapid additive metal sintering prototyping.",
            "status": InternshipProgram.Status.OPEN,
        },
    ]

    programs = []
    for p_data in programs_data:
        prog, _ = InternshipProgram.objects.get_or_create(
            program_code=p_data["program_code"],
            defaults=p_data,
        )
        programs.append(prog)

    # 2. Delete any invalid placements assigned to primary/high school or PUC students
    InternshipPlacement.objects.filter(
        Q(student__current_class__iregex=r"^(Class\s*([1-9]|10)|1st\s*PUC|2nd\s*PUC|PUC|11th|12th)")
        | Q(student__current_class__icontains="PUC")
    ).delete()

    # 3. Create or fetch Higher Education / Polytechnic & Degree Scholars
    eng_college, _ = School.objects.get_or_create(
        udise_code="29010200501",
        defaults={
            "name": "Govt. Engineering & Polytechnic Institute, Belagavi",
            "district": "Belagavi",
            "taluk": "Belagavi Urban",
            "address": "Udyambag Industrial Estate Road, Belagavi",
            "headmaster_name": "Dr. V. S. Hiremath",
            "status": School.Status.ACTIVE,
        }
    )
    sample_scholars = [
        ("ADM-ENG-001", "Karthik Deshpande", "B.E. Precision & Mechanical Engg", Student.Gender.MALE),
        ("ADM-ENG-002", "Pooja Hiremath", "B.Tech Information Technology & IoT", Student.Gender.FEMALE),
        ("ADM-ENG-003", "Sachin Kadam", "Diploma in Tool & Die Making", Student.Gender.MALE),
        ("ADM-ENG-004", "Sneha Joshi", "B.Sc Metrology & Quality Engineering", Student.Gender.FEMALE),
    ]
    higher_ed_students = []
    for adm, name, cls, gender in sample_scholars:
        s, _ = Student.objects.get_or_create(
            admission_number=adm,
            defaults={
                "student_name": name,
                "school": eng_college,
                "current_class": cls,
                "gender": gender,
                "status": Student.Status.ACTIVE,
            }
        )
        # Ensure class is up-to-date
        if s.current_class != cls:
            s.current_class = cls
            s.school = eng_college
            s.save()
        higher_ed_students.append(s)

    eligible_students = higher_ed_students

    # Seed clean, realistic placements for higher-ed scholars
    if not InternshipPlacement.objects.exists() and eligible_students:
        sample_placements = [
            (
                0, # Aero CNC
                0, # Karthik
                "Optimizing High-Speed CNC Toolpaths for Titanium Aerospace Brackets",
                InternshipPlacement.Status.IN_PROGRESS,
                Decimal("96.50"),
                InternshipPlacement.PerformanceGrade.EXCELLENT,
                Decimal("10000.00"),
                start_cur,
                end_cur,
                "Rajesh Kulkarni",
                "rajesh.kulkarni@aequs.com",
                "Demonstrates exceptional spatial comprehension and precision cutting tool setup skills on Mori Seiki 5-axis machines.",
                False,
            ),
            (
                1, # QA Metrology
                1, # Pooja
                "Automated Coordinate Measuring Machine (CMM) Inspection Calibration",
                InternshipPlacement.Status.IN_PROGRESS,
                Decimal("98.00"),
                InternshipPlacement.PerformanceGrade.OUTSTANDING,
                Decimal("9000.00"),
                start_cur,
                end_cur,
                "Deepa Patil",
                "deepa.patil@aequs.com",
                "Flawless calibration logs and thorough understanding of Zeiss Calypso metrology software routines.",
                False,
            ),
            (
                3, # Supply Chain
                2, # Sachin
                "ERP Inventory Lead-Time Optimization for Raw Ingot Logistics",
                InternshipPlacement.Status.COMPLETED,
                Decimal("100.00"),
                InternshipPlacement.PerformanceGrade.OUTSTANDING,
                Decimal("8500.00"),
                start_comp,
                end_comp,
                "Priyanka Naik",
                "priyanka.naik@aequs.com",
                "Successfully delivered an automated vendor re-order dashboard in SAP reducing stockout risk by 35%. Completed internship with top honors.",
                True,
            ),
            (
                0, # Aero CNC
                3, # Sneha
                "Surface Finish Roughness Enhancement in Aluminum Turbine Impellers",
                InternshipPlacement.Status.SELECTED,
                Decimal("92.00"),
                InternshipPlacement.PerformanceGrade.VERY_GOOD,
                Decimal("10000.00"),
                start_cur + datetime.timedelta(days=10),
                end_cur,
                "Rajesh Kulkarni",
                "rajesh.kulkarni@aequs.com",
                "Quick learner, currently completing introductory safety protocols and CAD blueprint verification.",
                False,
            ),
        ]

        for (
            prog_idx,
            student_idx,
            proj_title,
            status_val,
            att_val,
            grade_val,
            stipend_val,
            s_date,
            e_date,
            m_name,
            m_email,
            fb_text,
            cert_iss,
        ) in sample_placements:
            student = eligible_students[student_idx % len(eligible_students)]
            prog = programs[prog_idx % len(programs)]
            
            placement, created = InternshipPlacement.objects.get_or_create(
                student=student,
                program=prog,
                academic_year="2026-27",
                defaults={
                    "school": student.school,
                    "department": prog.department,
                    "company_name": prog.company_name,
                    "project_title": proj_title,
                    "start_date": s_date,
                    "end_date": e_date,
                    "stipend_amount": stipend_val,
                    "mentor_name": m_name,
                    "mentor_email": m_email,
                    "mentor_phone": "+91 98450 11223",
                    "status": status_val,
                    "attendance_percentage": att_val,
                    "performance_grade": grade_val,
                    "certificate_issued": cert_iss,
                    "evaluation_feedback": fb_text,
                }
            )

            if placement.certificate_issued and not placement.certificate_number:
                placement.certificate_number = generate_certificate_number(placement)
                placement.certificate_issue_date = end_comp
                placement.save()

            if created:
                InternshipMilestone.objects.create(
                    placement=placement,
                    title="Phase 1: Industrial Safety Protocols & CAD Familiarization",
                    due_date=placement.start_date + datetime.timedelta(days=14),
                    completed_date=placement.start_date + datetime.timedelta(days=12),
                    status=InternshipMilestone.MilestoneStatus.APPROVED,
                    mentor_comments="Completed all shopfloor safety drills and passed oral assessment.",
                )
                InternshipMilestone.objects.create(
                    placement=placement,
                    title="Phase 2: Live Machine Setup & Blueprint Tolerancing Practice",
                    due_date=placement.start_date + datetime.timedelta(days=35),
                    completed_date=placement.start_date + datetime.timedelta(days=34) if placement.status != InternshipPlacement.Status.SELECTED else None,
                    status=InternshipMilestone.MilestoneStatus.APPROVED if placement.status != InternshipPlacement.Status.SELECTED else InternshipMilestone.MilestoneStatus.IN_REVIEW,
                    mentor_comments="Good progress on workpiece centering and precision datum alignment.",
                )
