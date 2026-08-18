import os
import django
from decimal import Decimal
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import transaction
from schools.models import School
from students.models import Student
from academics.models import AcademicRecord
from eligibility.models import EligibilityRecord, BenefitType
from inventory.models import InventoryItem, InventoryCategory, Laptop, LaptopAssignment, StockTransaction
from distributions.models import Distribution, StudyKit, StudyKitItem, RecipientType, SchoolEssentialType, BenefitType as DistBenefitType
from internships.models import InternshipProgram, InternshipPlacement, Department
from events.models import Event
from volunteers.models import Volunteer, VolunteerActivity, EventParticipation

@transaction.atomic
def seed_all():
    print("🧹 Cleaning database...")
    EventParticipation.objects.all().delete()
    VolunteerActivity.objects.all().delete()
    Volunteer.objects.all().delete()
    Event.objects.all().delete()
    InternshipPlacement.objects.all().delete()
    InternshipProgram.objects.all().delete()
    Distribution.objects.all().delete()
    StudyKitItem.objects.all().delete()
    StudyKit.objects.all().delete()
    LaptopAssignment.objects.all().delete()
    Laptop.objects.all().delete()
    StockTransaction.objects.all().delete()
    InventoryItem.objects.all().delete()
    EligibilityRecord.objects.all().delete()
    AcademicRecord.objects.all().delete()
    Student.objects.all().delete()
    School.objects.all().delete()

    print("🏫 Creating Government Schools...")
    schools_data = [
        {
            "name": "Government High School Hukkeri",
            "udise_code": "29010100101",
            "address": "Main Road, Near Bus Stand, Hukkeri",
            "district": "Belagavi",
            "taluk": "Hukkeri",
            "village": "Hukkeri",
            "pincode": "591309",
            "phone": "08333-265120",
            "email": "ghs.hukkeri@karnataka.gov.in",
            "headmaster_name": "Dr. R. B. Patil",
            "headmaster_phone": "9845012345",
            "affiliation": "State",
            "status": School.Status.ACTIVE,
        },
        {
            "name": "Government High School Kittur",
            "udise_code": "29010200202",
            "address": "Fort Road, Rani Chennamma Nagar, Kittur",
            "district": "Belagavi",
            "taluk": "Kittur",
            "village": "Kittur",
            "pincode": "591115",
            "phone": "08288-234567",
            "email": "ghs.kittur@karnataka.gov.in",
            "headmaster_name": "Smt. Shailaja Joshi",
            "headmaster_phone": "9448123456",
            "affiliation": "State",
            "status": School.Status.ACTIVE,
        },
        {
            "name": "Government Composite PU College Belagavi",
            "udise_code": "29010300303",
            "address": "Club Road, Camp, Belagavi",
            "district": "Belagavi",
            "taluk": "Belagavi",
            "village": "Belagavi Urban",
            "pincode": "590001",
            "phone": "0831-2401234",
            "email": "gpuc.belagavi@karnataka.gov.in",
            "headmaster_name": "Prof. M. S. Kulkarni",
            "headmaster_phone": "9740112233",
            "affiliation": "State",
            "status": School.Status.ACTIVE,
        },
        {
            "name": "Government Model High School Gokak",
            "udise_code": "29010400404",
            "address": "Falls Road, Near Court Complex, Gokak",
            "district": "Belagavi",
            "taluk": "Gokak",
            "village": "Gokak",
            "pincode": "591307",
            "phone": "08332-225566",
            "email": "gmhs.gokak@karnataka.gov.in",
            "headmaster_name": "Sri. S. V. Koujalagi",
            "headmaster_phone": "9880123489",
            "affiliation": "State",
            "status": School.Status.ACTIVE,
        },
        {
            "name": "Rani Chennamma Memorial Model School",
            "udise_code": "29010500505",
            "address": "Station Road, Khanapur",
            "district": "Belagavi",
            "taluk": "Khanapur",
            "village": "Khanapur",
            "pincode": "591302",
            "phone": "08336-222333",
            "email": "rcms.khanapur@karnataka.gov.in",
            "headmaster_name": "Smt. Jayashree Deshmukh",
            "headmaster_phone": "9611223344",
            "affiliation": "State",
            "status": School.Status.ACTIVE,
        },
    ]

    schools = {}
    for s in schools_data:
        school_obj = School.objects.create(**s)
        schools[school_obj.name] = school_obj

    print(f"✅ Created {len(schools)} schools.")

    print("🎓 Creating Students and Academic Records...")
    students_specs = [
        # --- Class 5, 8, 9 (Standard Book Eligible) ---
        {"adm": "STU-2025-001", "name": "Aarav Patil", "gender": "MALE", "school": schools["Government High School Hukkeri"], "class": "Class 5", "sec": "A", "marks": 450, "total": 500, "pct": 90.00, "year": "2025-26"},
        {"adm": "STU-2025-002", "name": "Ananya Kulkarni", "gender": "FEMALE", "school": schools["Government High School Kittur"], "class": "Class 8", "sec": "B", "marks": 510, "total": 600, "pct": 85.00, "year": "2025-26"},
        {"adm": "STU-2025-003", "name": "Rohan Deshmukh", "gender": "MALE", "school": schools["Government Model High School Gokak"], "class": "Class 9", "sec": "A", "marks": 490, "total": 600, "pct": 81.67, "year": "2025-26"},
        {"adm": "STU-2025-004", "name": "Sneha Kamat", "gender": "FEMALE", "school": schools["Rani Chennamma Memorial Model School"], "class": "Class 9", "sec": "B", "marks": 520, "total": 600, "pct": 86.67, "year": "2025-26"},

        # --- Class 10 (Books + Workbooks + Top 10 Merit Study Kit) ---
        {"adm": "STU-2025-010", "name": "Pooja Hiremath", "gender": "FEMALE", "school": schools["Government High School Hukkeri"], "class": "Class 10", "sec": "A", "marks": 585, "total": 625, "pct": 93.60, "rank": 1, "year": "2025-26"},
        {"adm": "STU-2025-011", "name": "Kiran Biradar", "gender": "MALE", "school": schools["Government High School Kittur"], "class": "Class 10", "sec": "A", "marks": 578, "total": 625, "pct": 92.48, "rank": 2, "year": "2025-26"},
        {"adm": "STU-2025-012", "name": "Megha Joshi", "gender": "FEMALE", "school": schools["Government Model High School Gokak"], "class": "Class 10", "sec": "B", "marks": 568, "total": 625, "pct": 90.88, "rank": 3, "year": "2025-26"},
        {"adm": "STU-2025-013", "name": "Siddharth Naik", "gender": "MALE", "school": schools["Rani Chennamma Memorial Model School"], "class": "Class 10", "sec": "A", "marks": 555, "total": 625, "pct": 88.80, "rank": 4, "year": "2025-26"},
        {"adm": "STU-2025-014", "name": "Deepa Angadi", "gender": "FEMALE", "school": schools["Government High School Hukkeri"], "class": "Class 10", "sec": "B", "marks": 545, "total": 625, "pct": 87.20, "rank": 5, "year": "2025-26"},
        {"adm": "STU-2025-015", "name": "Manjunath Koujalagi", "gender": "MALE", "school": schools["Government High School Kittur"], "class": "Class 10", "sec": "B", "marks": 535, "total": 625, "pct": 85.60, "rank": 6, "year": "2025-26"},
        {"adm": "STU-2025-016", "name": "Shilpa Patil", "gender": "FEMALE", "school": schools["Government Model High School Gokak"], "class": "Class 10", "sec": "A", "marks": 525, "total": 625, "pct": 84.00, "rank": 7, "year": "2025-26"},
        {"adm": "STU-2025-017", "name": "Basavaraj Meti", "gender": "MALE", "school": schools["Rani Chennamma Memorial Model School"], "class": "Class 10", "sec": "B", "marks": 515, "total": 625, "pct": 82.40, "rank": 8, "year": "2025-26"},
        {"adm": "STU-2025-018", "name": "Rashmi Hegde", "gender": "FEMALE", "school": schools["Government High School Hukkeri"], "class": "Class 10", "sec": "A", "marks": 508, "total": 625, "pct": 81.28, "rank": 9, "year": "2025-26"},
        {"adm": "STU-2025-019", "name": "Vinay Chougule", "gender": "MALE", "school": schools["Government High School Kittur"], "class": "Class 10", "sec": "A", "marks": 498, "total": 625, "pct": 79.68, "rank": 10, "year": "2025-26"},
        {"adm": "STU-2025-020", "name": "Akash Shinde", "gender": "MALE", "school": schools["Government Model High School Gokak"], "class": "Class 10", "sec": "C", "marks": 435, "total": 625, "pct": 69.60, "rank": 18, "year": "2025-26"},

        # --- 1st & 2nd PUC (Pre-University Study Kit Continuation + 2nd PUC Laptop Qualifying) ---
        {"adm": "STU-2025-030", "name": "Kavya Patil", "gender": "FEMALE", "school": schools["Government Composite PU College Belagavi"], "class": "1st PUC Science", "sec": "A", "marks": 530, "total": 600, "pct": 88.33, "year": "2025-26", "has_prev_studykit": True},
        {"adm": "STU-2025-031", "name": "Praveen Hubballi", "gender": "MALE", "school": schools["Government Composite PU College Belagavi"], "class": "1st PUC Commerce", "sec": "B", "marks": 512, "total": 600, "pct": 85.33, "year": "2025-26", "has_prev_studykit": True},
        {"adm": "STU-2025-032", "name": "Suresh Belagavi", "gender": "MALE", "school": schools["Government Composite PU College Belagavi"], "class": "2nd PUC Science", "sec": "A", "marks": 582, "total": 600, "pct": 97.00, "rank": 1, "year": "2025-26", "has_prev_studykit": True},
        {"adm": "STU-2025-033", "name": "Aishwarya Gouda", "gender": "FEMALE", "school": schools["Government Composite PU College Belagavi"], "class": "2nd PUC Science", "sec": "A", "marks": 572, "total": 600, "pct": 95.33, "rank": 2, "year": "2025-26", "has_prev_studykit": True},
        {"adm": "STU-2025-034", "name": "Naveen Badiger", "gender": "MALE", "school": schools["Government Composite PU College Belagavi"], "class": "2nd PUC Commerce", "sec": "A", "marks": 560, "total": 600, "pct": 93.33, "rank": 3, "year": "2025-26", "has_prev_studykit": True},
        {"adm": "STU-2025-035", "name": "Vidya Pujar", "gender": "FEMALE", "school": schools["Government Composite PU College Belagavi"], "class": "2nd PUC Science", "sec": "B", "marks": 548, "total": 600, "pct": 91.33, "rank": 4, "year": "2025-26", "has_prev_studykit": True},
        {"adm": "STU-2025-036", "name": "Ganesh Pujari", "gender": "MALE", "school": schools["Government Composite PU College Belagavi"], "class": "2nd PUC Science", "sec": "B", "marks": 535, "total": 600, "pct": 89.17, "rank": 5, "year": "2025-26", "has_prev_studykit": False},

        # --- Diploma 3rd Year (Laptop Qualifying & Internship Candidates) ---
        {"adm": "STU-2025-040", "name": "Sachin Jadhav", "gender": "MALE", "school": schools["Government Composite PU College Belagavi"], "class": "Diploma 3rd Year Mechanical", "sec": "A", "marks": 895, "total": 1000, "pct": 89.50, "rank": 6, "year": "2025-26"},
        {"adm": "STU-2025-041", "name": "Priyanka Desai", "gender": "FEMALE", "school": schools["Government Composite PU College Belagavi"], "class": "Diploma 3rd Year Computer Science", "sec": "A", "marks": 876, "total": 1000, "pct": 87.60, "rank": 7, "year": "2025-26"},

        # --- Degree 1st Year (Laptop Distribution Stage & Corporate Internship Eligible) ---
        {"adm": "STU-2025-050", "name": "Aditya Kulkarni", "gender": "MALE", "school": schools["Government Composite PU College Belagavi"], "class": "Degree 1st Year (B.E. Mechanical)", "sec": "A", "marks": 850, "total": 1000, "pct": 85.00, "year": "2025-26", "has_prev_laptop": True},
        {"adm": "STU-2025-051", "name": "Soumya Hanchinal", "gender": "FEMALE", "school": schools["Government Composite PU College Belagavi"], "class": "Degree 1st Year (BCA)", "sec": "A", "marks": 880, "total": 1000, "pct": 88.00, "year": "2025-26", "has_prev_laptop": True},
        {"adm": "STU-2025-052", "name": "Darshan Marathe", "gender": "MALE", "school": schools["Government Composite PU College Belagavi"], "class": "Degree 1st Year (B.Tech Robotics)", "sec": "A", "marks": 865, "total": 1000, "pct": 86.50, "year": "2025-26", "has_prev_laptop": True},
        {"adm": "STU-2025-053", "name": "Tejaswini Hosur", "gender": "FEMALE", "school": schools["Government Composite PU College Belagavi"], "class": "BE 2nd Year (Lateral Entry)", "sec": "A", "marks": 840, "total": 1000, "pct": 84.00, "year": "2025-26", "has_prev_laptop": True},
    ]

    students = {}
    for spec in students_specs:
        st = Student.objects.create(
            admission_number=spec["adm"],
            student_name=spec["name"],
            gender=spec["gender"],
            school=spec["school"],
            current_class=spec["class"],
            section=spec["sec"],
            date_of_birth=date(2008, 5, 15),
            status=Student.Status.ACTIVE,
        )
        students[spec["name"]] = st

        # Create Academic Record
        AcademicRecord.objects.create(
            student=st,
            academic_year=spec["year"],
            class_or_course=spec["class"],
            marks_obtained=Decimal(str(spec["marks"])),
            total_marks=Decimal(str(spec["total"])),
            percentage=Decimal(str(spec["pct"])),
            rank=spec.get("rank"),
            promotion_status="Promoted",
        )

        # Create previous eligibility if continuation prerequisite
        if spec.get("has_prev_studykit"):
            EligibilityRecord.objects.create(
                student=st,
                benefit_type=BenefitType.STUDY_KIT,
                academic_year="2024-25",
                eligible=True,
                selection_rank=1,
                reason="Merit Scholar in Class 10 (2024-25).",
            )
        if spec.get("has_prev_laptop"):
            EligibilityRecord.objects.create(
                student=st,
                benefit_type=BenefitType.LAPTOP,
                academic_year="2024-25",
                eligible=True,
                selection_rank=1,
                reason="Top Merit Scholar in 2nd PUC / Diploma (2024-25 Qualifying Stage).",
            )

    print(f"✅ Created {len(students)} students with academic history.")

    print("⚙️ Running Benefit Eligibility Engine for Academic Year 2025-26...")
    from eligibility.services import generate_all_eligibility
    generate_all_eligibility("2025-26")

    print(f"✅ Generated {EligibilityRecord.objects.count()} verified eligibility records.")

    print("📦 Creating Configurable Study Kits...")
    kit_primary = StudyKit.objects.create(
        name="Primary STEM Explorer Kit",
        target_grade_level="Class 1 to 5",
        description="Foundational Math manipulatives, basic science flashcards, geometry ruler, and coloring pack.",
    )
    StudyKitItem.objects.create(kit=kit_primary, item_name="Geometry Tool Set", quantity_per_kit=1, specification="Standard primary school set")
    StudyKitItem.objects.create(kit=kit_primary, item_name="Math Flashcards & Manipulatives", quantity_per_kit=1, specification="Laminated card pack")
    StudyKitItem.objects.create(kit=kit_primary, item_name="Basic Science Concept Workbook", quantity_per_kit=1, specification="Illustrated practice book")

    kit_sslc = StudyKit.objects.create(
        name="High School SSLC Merit Kit",
        target_grade_level="Class 10",
        description="Comprehensive board prep guide, scientific calculator, technical drawing set, and reference charts.",
    )
    StudyKitItem.objects.create(kit=kit_sslc, item_name="Scientific Calculator (Fx-82MS)", quantity_per_kit=1, specification="Casio non-programmable")
    StudyKitItem.objects.create(kit=kit_sslc, item_name="SSLC Model Question Bank & Formula Chart", quantity_per_kit=2, specification="State Board 2026 Edition")
    StudyKitItem.objects.create(kit=kit_sslc, item_name="Technical Drawing Instrument Box", quantity_per_kit=1, specification="Steel compass & dividers")

    kit_puc = StudyKit.objects.create(
        name="Pre-University Science & Tech Kit",
        target_grade_level="1st & 2nd PUC / Diploma",
        description="Advanced physics/chemistry handbook, engineering compass, lab logbooks, and scientific reference materials.",
    )
    StudyKitItem.objects.create(kit=kit_puc, item_name="Advanced Scientific Calculator", quantity_per_kit=1, specification="12-digit dual power")
    StudyKitItem.objects.create(kit=kit_puc, item_name="Engineering Graphics Set", quantity_per_kit=1, specification="Mini drafter & T-square")
    StudyKitItem.objects.create(kit=kit_puc, item_name="Science Laboratory Logbook", quantity_per_kit=2, specification="Hardbound graph & ledger")

    print("📊 Creating Inventory Items...")
    inv_items = [
        {"name": "Karnataka State Board Textbooks (Class 1-10)", "sku": "BK-KSTB-1-10", "category": InventoryCategory.BOOKS, "unit": "Sets", "stock": 450, "threshold": 50, "cost": 420.00, "loc": "Main Warehouse A-1"},
        {"name": "SSLC Class 10 Board Exam Workbooks", "sku": "WB-SSLC-2026", "category": InventoryCategory.WORKBOOKS, "unit": "Copies", "stock": 180, "threshold": 25, "cost": 180.00, "loc": "Main Warehouse A-2"},
        {"name": "SSLC Merit Study Kits Pack", "sku": "SK-HS-MERIT", "category": InventoryCategory.STUDY_KITS, "unit": "Kits", "stock": 65, "threshold": 15, "cost": 1250.00, "loc": "Assembly Room B-1"},
        {"name": "Pre-University Science & Tech Kits", "sku": "SK-PUC-SCI", "category": InventoryCategory.STUDY_KITS, "unit": "Kits", "stock": 40, "threshold": 10, "cost": 1600.00, "loc": "Assembly Room B-2"},
        {"name": "Dell Latitude 5420 Laptop i5/16GB/512GB", "sku": "LAP-DELL-5420", "category": InventoryCategory.LAPTOPS, "unit": "Units", "stock": 8, "threshold": 2, "cost": 48500.00, "loc": "IT Secure Locker C-1"},
        {"name": "HP EliteBook 840 G8 Laptop i5/16GB", "sku": "LAP-HP-840G8", "category": InventoryCategory.LAPTOPS, "unit": "Units", "stock": 6, "threshold": 2, "cost": 52000.00, "loc": "IT Secure Locker C-1"},
        {"name": "Dual Student Desks & Benches Set", "sku": "SE-DUAL-BENCH", "category": InventoryCategory.SCHOOL_ESSENTIALS, "unit": "Sets", "stock": 85, "threshold": 10, "cost": 3800.00, "loc": "Furniture Warehouse D"},
        {"name": "Commercial RO Water Purification System (50 LPH)", "sku": "SE-RO-50LPH", "category": InventoryCategory.SCHOOL_ESSENTIALS, "unit": "Units", "stock": 12, "threshold": 3, "cost": 22000.00, "loc": "Appliance Storage E"},
        {"name": "Interactive Magnetic Ceramic Whiteboards (6x4 ft)", "sku": "SE-WB-6X4", "category": InventoryCategory.SCHOOL_ESSENTIALS, "unit": "Units", "stock": 24, "threshold": 5, "cost": 4500.00, "loc": "Appliance Storage E"},
        {"name": "School Sports Equipment & Cricket Kit", "sku": "SE-SPORTS-KIT", "category": InventoryCategory.SCHOOL_ESSENTIALS, "unit": "Kits", "stock": 18, "threshold": 4, "cost": 6500.00, "loc": "Recreation Bay F"},
    ]

    for item in inv_items:
        InventoryItem.objects.create(
            item_name=item["name"],
            sku=item["sku"],
            category=item["category"],
            unit=item["unit"],
            current_stock=item["stock"],
            low_stock_threshold=item["threshold"],
            unit_cost=Decimal(str(item["cost"])),
            location=item["loc"],
            description="Verified EduTrack CSR inventory supply.",
        )

    print("💻 Creating Laptop Inventory & Assignments...")
    laptop_models = [
        {"asset": "AEQ-LAP-2026-001", "brand": "Dell", "model": "Latitude 5420", "serial": "CN-0G6T1-74411-26A", "cost": 48500.00, "status": Laptop.Status.ISSUED},
        {"asset": "AEQ-LAP-2026-002", "brand": "Dell", "model": "Latitude 5420", "serial": "CN-0G6T1-74411-26B", "cost": 48500.00, "status": Laptop.Status.ISSUED},
        {"asset": "AEQ-LAP-2026-003", "brand": "HP", "model": "EliteBook 840 G8", "serial": "5CG142099A", "cost": 52000.00, "status": Laptop.Status.ISSUED},
        {"asset": "AEQ-LAP-2026-004", "brand": "HP", "model": "EliteBook 840 G8", "serial": "5CG142099B", "cost": 52000.00, "status": Laptop.Status.ISSUED},
        {"asset": "AEQ-LAP-2026-005", "brand": "Dell", "model": "Latitude 5420", "serial": "CN-0G6T1-74411-26C", "cost": 48500.00, "status": Laptop.Status.AVAILABLE},
        {"asset": "AEQ-LAP-2026-006", "brand": "Dell", "model": "Latitude 5420", "serial": "CN-0G6T1-74411-26D", "cost": 48500.00, "status": Laptop.Status.AVAILABLE},
        {"asset": "AEQ-LAP-2026-007", "brand": "HP", "model": "EliteBook 840 G8", "serial": "5CG142099C", "cost": 52000.00, "status": Laptop.Status.AVAILABLE},
        {"asset": "AEQ-LAP-2026-008", "brand": "Lenovo", "model": "ThinkPad E14 Gen 4", "serial": "PF399120", "cost": 49000.00, "status": Laptop.Status.AVAILABLE},
    ]

    laptops = {}
    for lm in laptop_models:
        lap = Laptop.objects.create(
            asset_number=lm["asset"],
            brand=lm["brand"],
            model_name=lm["model"],
            serial_number=lm["serial"],
            purchase_date=date(2026, 1, 15),
            purchase_cost=Decimal(str(lm["cost"])),
            condition=Laptop.Condition.NEW,
            status=lm["status"],
            warranty_expiry=date(2029, 1, 15),
            notes="Aequs Education CSR merit incentive device.",
        )
        laptops[lm["asset"]] = lap

    # Create Laptop Assignments for our top Degree students
    degree_laptop_recipients = [
        ("Aditya Kulkarni", "AEQ-LAP-2026-001"),
        ("Soumya Hanchinal", "AEQ-LAP-2026-002"),
        ("Darshan Marathe", "AEQ-LAP-2026-003"),
        ("Tejaswini Hosur", "AEQ-LAP-2026-004"),
    ]

    for student_name, asset_tag in degree_laptop_recipients:
        st = students[student_name]
        lap = laptops[asset_tag]
        LaptopAssignment.objects.create(
            laptop=lap,
            student=st,
            academic_year="2025-26",
            status=LaptopAssignment.Status.ISSUED,
            issue_notes=f"Issued for higher technical education under Aequs Merit Scholarship program.",
        )

    print("🚚 Creating Real Distributions...")
    # Student Benefit Distributions
    dist_book = Distribution.objects.create(
        recipient_type=RecipientType.STUDENT,
        student=students["Aarav Patil"],
        benefit_type=DistBenefitType.BOOK,
        academic_year="2025-26",
        distribution_date=date.today() - timedelta(days=20),
        remarks="Delivered complete Class 5 curriculum books set.",
    )

    dist_wb = Distribution.objects.create(
        recipient_type=RecipientType.STUDENT,
        student=students["Pooja Hiremath"],
        benefit_type=DistBenefitType.WORKBOOK,
        academic_year="2025-26",
        distribution_date=date.today() - timedelta(days=15),
        remarks="Issued Class 10 Board exam master prep workbooks.",
    )

    dist_kit = Distribution.objects.create(
        recipient_type=RecipientType.STUDENT,
        student=students["Pooja Hiremath"],
        study_kit=kit_sslc,
        benefit_type=DistBenefitType.STUDY_KIT,
        academic_year="2025-26",
        distribution_date=date.today() - timedelta(days=12),
        remarks="Awarded Top 10 Merit Scholar SSLC Study Kit.",
    )

    dist_lap = Distribution.objects.create(
        recipient_type=RecipientType.STUDENT,
        student=students["Aditya Kulkarni"],
        benefit_type=DistBenefitType.LAPTOP,
        academic_year="2025-26",
        distribution_date=date.today() - timedelta(days=5),
        remarks="Delivered Dell Latitude 5420 for B.E. Mechanical degree studies.",
    )

    # School Essential Distributions
    dist_school_1 = Distribution.objects.create(
        recipient_type=RecipientType.SCHOOL,
        school=schools["Government High School Kittur"],
        benefit_type=DistBenefitType.SCHOOL_ESSENTIAL,
        essential_item_type=SchoolEssentialType.BENCHES,
        academic_year="2025-26",
        distribution_date=date.today() - timedelta(days=18),
        remarks="Installed 25 sets of Dual Desks and Benches for Class 9 & 10 classrooms.",
    )

    dist_school_2 = Distribution.objects.create(
        recipient_type=RecipientType.SCHOOL,
        school=schools["Government High School Hukkeri"],
        benefit_type=DistBenefitType.SCHOOL_ESSENTIAL,
        essential_item_type=SchoolEssentialType.WATER_FILTERS,
        academic_year="2025-26",
        distribution_date=date.today() - timedelta(days=10),
        remarks="Commissioned 50 LPH RO Drinking Water Filtration Plant.",
    )

    print("💼 Creating Corporate Internship Programs & Placements...")
    prog_1 = InternshipProgram.objects.create(
        title="Aequs Aerospace Precision Engineering Apprenticeship",
        program_code="AEQ-INT-2026-01",
        company_name="Aequs Aerospace SEZ",
        department=Department.AEROSPACE_ENG,
        location="Belagavi SEZ, Karnataka",
        duration_months=6,
        stipend_amount=Decimal("12000.00"),
        total_slots=10,
        academic_year="2025-26",
        start_date=date.today() + timedelta(days=15),
        end_date=date.today() + timedelta(days=195),
        eligibility_criteria="B.E. Mechanical / Aerospace / Mechatronics degree students or Diploma with 80%+ marks.",
        mentor_in_charge="Rajesh Sharma (Lead Metrology Specialist)",
        mentor_contact="rajesh.sharma@aequs.com",
        status=InternshipProgram.Status.OPEN,
    )

    prog_2 = InternshipProgram.objects.create(
        title="Advanced CNC Machining & Quality Metrology Track",
        program_code="AEQ-INT-2026-02",
        company_name="Aequs Precision Manufacturing",
        department=Department.PRECISION_MANUFACTURING,
        location="Belagavi SEZ, Karnataka",
        duration_months=3,
        stipend_amount=Decimal("10000.00"),
        total_slots=15,
        academic_year="2025-26",
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=100),
        eligibility_criteria="Final year Diploma (Mechanical / Tool & Die) or Degree Engineering students.",
        mentor_in_charge="Sunil Patil (Operations Head)",
        mentor_contact="sunil.patil@aequs.com",
        status=InternshipProgram.Status.IN_PROGRESS,
    )

    prog_3 = InternshipProgram.objects.create(
        title="Industrial IoT & Smart Factory Systems Internship",
        program_code="AEQ-INT-2026-03",
        company_name="Aequs Digital & Software Division",
        department=Department.IT_AND_SOFTWARE,
        location="Belagavi SEZ / Hybrid",
        duration_months=4,
        stipend_amount=Decimal("15000.00"),
        total_slots=8,
        academic_year="2025-26",
        start_date=date.today() + timedelta(days=20),
        end_date=date.today() + timedelta(days=140),
        eligibility_criteria="BCA / B.Tech Computer Science / Robotics students.",
        mentor_in_charge="Priya Nair (Senior Software Architect)",
        mentor_contact="priya.nair@aequs.com",
        status=InternshipProgram.Status.OPEN,
    )

    # Candidate placements
    InternshipPlacement.objects.create(
        program=prog_1,
        student=students["Aditya Kulkarni"],
        school=students["Aditya Kulkarni"].school,
        academic_year="2025-26",
        department=prog_1.department,
        company_name=prog_1.company_name,
        project_title="Precision Milling & Aerospace Component Quality Verification",
        mentor_name="Rajesh Sharma",
        stipend_amount=Decimal("12000.00"),
        status=InternshipPlacement.Status.SELECTED,
    )

    InternshipPlacement.objects.create(
        program=prog_2,
        student=students["Sachin Jadhav"],
        school=students["Sachin Jadhav"].school,
        academic_year="2025-26",
        department=prog_2.department,
        company_name=prog_2.company_name,
        project_title="Multi-Axis CNC Programming & Metrology Analysis",
        mentor_name="Sunil Patil",
        stipend_amount=Decimal("10000.00"),
        status=InternshipPlacement.Status.IN_PROGRESS,
    )

    InternshipPlacement.objects.create(
        program=prog_3,
        student=students["Soumya Hanchinal"],
        school=students["Soumya Hanchinal"].school,
        academic_year="2025-26",
        department=prog_3.department,
        company_name=prog_3.company_name,
        project_title="Smart Factory IoT Telemetry & Analytics Dashboard",
        mentor_name="Priya Nair",
        stipend_amount=Decimal("15000.00"),
        status=InternshipPlacement.Status.SELECTED,
    )

    print("📅 Creating CSR Events & Volunteers...")
    event_1 = Event.objects.create(
        title="Annual EduTrack Merit Scholarship & Kit Distribution 2026",
        description="Celebration and handover of SSLC Study Kits and Merit Laptops to top performers from government schools.",
        event_date=date.today() - timedelta(days=10),
        location="Belagavi SEZ Convention Hall",
        organizer="Aequs Corporate Social Responsibility Foundation",
    )

    event_2 = Event.objects.create(
        title="Government Schools STEM & Robotics Innovation Fair",
        description="Interactive science exhibits, robotics demos, and hands-on lab experiments for rural students.",
        event_date=date.today() + timedelta(days=25),
        location="Kittur Fort Grounds Community Hall",
        organizer="EduTrack Educational Outreach Cell",
    )

    vol_1 = Volunteer.objects.create(
        first_name="Mahesh",
        last_name="Gokak",
        email="mahesh.gokak@aequs.com",
        phone="9845098765",
        gender="MALE",
        city="Belagavi",
        occupation="Senior Design Engineer at Aequs",
        qualification="M.Tech Mechanical",
        skills="STEM Mentoring, Career Guidance, Math Tutoring",
        status="ACTIVE",
    )

    vol_2 = Volunteer.objects.create(
        first_name="Anita",
        last_name="Desai",
        email="anita.desai@gmail.com",
        phone="9740123987",
        gender="FEMALE",
        city="Hubballi",
        occupation="Educational Consultant",
        qualification="M.Sc Physics, B.Ed",
        skills="Science Experiments, Student Counselling",
        status="ACTIVE",
    )

    VolunteerActivity.objects.create(
        volunteer=vol_1,
        activity_name="SSLC Board Exam Career Counseling Workshop",
        activity_date=date.today() - timedelta(days=8),
        status="COMPLETED",
        description="Conducted orientation session for Class 10 students on technical career streams.",
        remarks="Covered engineering, diploma, and technical career opportunities.",
    )

    EventParticipation.objects.create(
        volunteer=vol_1,
        event=event_1,
        role="Master of Ceremonies",
        participation_status="ATTENDED",
        hours_contributed=Decimal("6.0"),
        remarks="Managed the stage distribution and scholar felicitation ceremony.",
    )

    EventParticipation.objects.create(
        volunteer=vol_2,
        event=event_1,
        role="Logistics & Kit Desk Coordinator",
        participation_status="ATTENDED",
        hours_contributed=Decimal("5.0"),
        remarks="Coordinated kit verification and delivery desks for students.",
    )

    print("\n🎉 ALL SEED DATA SUCCESSFULLY INITIALIZED!")
    print(f"Schools: {School.objects.count()}")
    print(f"Students: {Student.objects.count()}")
    print(f"Academic Records: {AcademicRecord.objects.count()}")
    print(f"Eligibility Records: {EligibilityRecord.objects.count()}")
    print(f"Inventory Items: {InventoryItem.objects.count()}")
    print(f"Laptops (Total): {Laptop.objects.count()} (Issued: {Laptop.objects.filter(status='ISSUED').count()}, Available: {Laptop.objects.filter(status='AVAILABLE').count()})")
    print(f"Laptop Assignments: {LaptopAssignment.objects.count()}")
    print(f"Distributions: {Distribution.objects.count()}")
    print(f"Internship Programs: {InternshipProgram.objects.count()} (Placements: {InternshipPlacement.objects.count()})")
    print(f"Events: {Event.objects.count()}")
    print(f"Volunteers: {Volunteer.objects.count()}")

if __name__ == '__main__':
    seed_all()
