import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import (
    InventoryCategory,
    InventoryItem,
    StockTransaction,
    Laptop,
    LaptopAssignment,
)
from distributions.models import (
    Distribution,
    BenefitType,
    RecipientType,
    SchoolEssentialType,
    StudyKit,
    StudyKitItem,
)
from students.models import Student
from schools.models import School, SchoolResource
from academics.models import AcademicRecord


class Command(BaseCommand):
    help = "Seed complete demo dataset for Books, Workbooks, Study Kits, Laptops, 11 School Essentials, Top PUC Students, and Stock Tracking"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding comprehensive Inventory & Distribution ecosystem..."))

        # Clear existing transactions & distributions
        Distribution.objects.all().delete()
        StockTransaction.objects.all().delete()
        LaptopAssignment.objects.all().delete()
        Laptop.objects.all().delete()
        InventoryItem.objects.all().delete()
        StudyKitItem.objects.all().delete()
        StudyKit.objects.all().delete()

        # 1. Schools
        schools_data = [
            ("Govt. Model High School Jayanagar", "29010200301", "Bangalore Urban", "Jayanagar 4th Block"),
            ("Govt. Pre-University College Malleshwaram", "29010200405", "Bangalore Urban", "Malleshwaram 18th Cross"),
            ("Govt. Composite High School Belagavi", "29020100112", "Belagavi", "Camp Area"),
            ("Govt. Higher Primary School Hubballi", "29030100223", "Dharwad", "Vidyanagar"),
        ]
        created_schools = []
        for name, udise, dist, loc in schools_data:
            sch, _ = School.objects.get_or_create(
                udise_code=udise,
                defaults={
                    "name": name,
                    "district": dist,
                    "village": loc,
                    "address": f"{loc}, {dist}",
                    "headmaster_name": f"Principal of {name}",
                }
            )
            created_schools.append(sch)

        main_school = created_schools[0]
        puc_college = created_schools[1]

        # 2. Students & Academic Records (including Top PUC Merit students)
        students_dataset = [
            # Top PUC Students (Merit Laptop Scholarship Candidates)
            ("Aditi Hegde", "ADM-PUC-001", "2nd PUC", puc_college, 96.5, 1),
            ("Chirag Patil", "ADM-PUC-002", "2nd PUC", puc_college, 95.2, 2),
            ("Bhavana Kulkarni", "ADM-PUC-003", "2nd PUC", puc_college, 94.0, 3),
            ("Darshan Naik", "ADM-PUC-004", "2nd PUC", puc_college, 93.4, 4),
            ("Gautam Joshi", "ADM-PUC-005", "1st PUC", puc_college, 92.8, 5),
            ("Ishita Rao", "ADM-PUC-006", "1st PUC", puc_college, 91.5, 6),
            ("Kiran Deshpande", "ADM-PUC-007", "2nd PUC", puc_college, 90.2, 7),
            ("Meera Shenoy", "ADM-PUC-008", "1st PUC", puc_college, 89.6, 8),
            ("Nikhil Kulkarni", "ADM-PUC-009", "2nd PUC", puc_college, 88.5, 9),
            ("Pranav Bhat", "ADM-PUC-010", "2nd PUC", puc_college, 87.8, 10),
            ("Rohit Kamat", "ADM-PUC-011", "1st PUC", puc_college, 84.0, 15),

            # Class 10 Students (Eligible for Class 10 Workbooks & Books)
            ("Aarav Sharma", "ADM-2024-101", "Class 10", main_school, 88.0, 4),
            ("Diya Patel", "ADM-2024-102", "Class 10", main_school, 86.5, 5),
            ("Sameer Khan", "ADM-2024-103", "Class 10", main_school, 78.0, 12),
            ("Tanvi Shettigar", "ADM-2024-104", "Class 10", main_school, 92.0, 2),

            # Class 1 to 9 Students (Eligible for Books and Study Kits)
            ("Rohan Gupta", "ADM-2024-003", "Class 9", main_school, 82.0, 8),
            ("Sanya Iyer", "ADM-2024-004", "Class 8", main_school, 79.5, 11),
            ("Kavya Reddy", "ADM-2024-005", "Class 7", main_school, 85.0, 6),
            ("Varun Kumar", "ADM-2024-006", "Class 6", main_school, 74.0, 14),
            ("Pooja Naik", "ADM-2024-007", "Class 5", main_school, 89.0, 3),
            ("Manoj Shetty", "ADM-2024-008", "Class 4", main_school, 80.0, 9),
        ]

        student_objs = {}
        for name, adm, cls, sch, pct, rnk in students_dataset:
            st, _ = Student.objects.get_or_create(
                admission_number=adm,
                defaults={
                    "student_name": name,
                    "school": sch,
                    "current_class": cls,
                    "gender": Student.Gender.FEMALE if ("Aditi" in name or "Bhavana" in name or "Diya" in name or "Ishita" in name or "Kavya" in name or "Meera" in name or "Pooja" in name or "Sanya" in name or "Tanvi" in name) else Student.Gender.MALE,
                    "parent_name": f"Parent of {name}",
                }
            )
            student_objs[adm] = st

            # Academic record
            AcademicRecord.objects.get_or_create(
                student=st,
                academic_year="2024-2025",
                class_or_course=cls,
                defaults={
                    "percentage": Decimal(str(pct)),
                    "rank": rnk,
                    "promotion_status": "Promoted",
                    "marks_obtained": Decimal(str(pct * 6)),
                    "total_marks": Decimal("600.00"),
                }
            )

        # 3. Study Kits (Module 8)
        kit1 = StudyKit.objects.create(
            name="Primary STEM & Activity Kit (Class 1–5)",
            target_grade_level="Class 1 to 5",
            description="Foundation learning supplies including drawing pad, color crayons, pencils, eraser, and mini geometry ruler",
        )
        StudyKitItem.objects.create(kit=kit1, item_name="Primary Drawing & Sketch Book", quantity_per_kit=2)
        StudyKitItem.objects.create(kit=kit1, item_name="Non-Toxic Wax Crayons (Pack of 16)", quantity_per_kit=1)
        StudyKitItem.objects.create(kit=kit1, item_name="Lead Pencils & Eraser Set", quantity_per_kit=1)

        kit2 = StudyKit.objects.create(
            name="High School Comprehensive Study Kit (Class 6–10)",
            target_grade_level="Class 6 to 10",
            description="Comprehensive kit with 6 long ruled notebooks, mathematical geometry instrument box, pen pouch, and highlighters",
        )
        StudyKitItem.objects.create(kit=kit2, item_name="192-Page Long Ruled Notebooks", quantity_per_kit=6)
        StudyKitItem.objects.create(kit=kit2, item_name="Mathematical Instruments Geometry Box", quantity_per_kit=1)
        StudyKitItem.objects.create(kit=kit2, item_name="Gel Pen Set with Zip Pouch", quantity_per_kit=1)

        kit3 = StudyKit.objects.create(
            name="PUC Science & Engineering Practical Kit (1st & 2nd PUC)",
            target_grade_level="1st & 2nd PUC",
            description="Senior secondary practical STEM kit with scientific calculator, lab record notebooks, and dissection/circuit tools",
        )
        StudyKitItem.objects.create(kit=kit3, item_name="Hardcover Lab Practical Record Books", quantity_per_kit=4)
        StudyKitItem.objects.create(kit=kit3, item_name="Scientific Calculator FX-82MS", quantity_per_kit=1)
        StudyKitItem.objects.create(kit=kit3, item_name="STEM Drafting Compass & Scale Ruler Set", quantity_per_kit=1)

        # 4. Inventory Items (Including 11 Government School Essentials)
        inventory_items_master = [
            # 1. BOOKS
            ("Class 10 NCERT Mathematics", "BK-NCERT-M10", InventoryCategory.BOOKS, "Copies", 140, 30, 160.00, "Warehouse A - B1", "Class 10 State Syllabus Mathematics Textbook"),
            ("Class 9 NCERT Science & Technology", "BK-NCERT-S09", InventoryCategory.BOOKS, "Copies", 85, 25, 150.00, "Warehouse A - B1", "Class 9 Core Science textbook"),
            ("Class 8 Social Studies & Civics", "BK-SOC-08", InventoryCategory.BOOKS, "Copies", 12, 25, 130.00, "Warehouse A - B2", "History, Geography, and Civics integrated text"),
            ("English Grammar & Reader - Class 6", "BK-ENG-06", InventoryCategory.BOOKS, "Copies", 0, 20, 110.00, "Warehouse A - B3", "Foundation English literature & workbook"),

            # 2. WORKBOOKS (Class 10 specific)
            ("Class 10 Board Exam Science Practical Workbook", "WB-SCI-10", InventoryCategory.WORKBOOKS, "Workbooks", 100, 20, 95.00, "Warehouse A - W1", "Comprehensive Class 10 Science practical activities and exam prep"),
            ("Class 10 Mathematics Question Bank & Practice Workbook", "WB-MATH-10", InventoryCategory.WORKBOOKS, "Workbooks", 90, 20, 90.00, "Warehouse A - W1", "Class 10 solved questions and model test papers"),
            ("STEM Practical Science Experiment Workbook Grade 8", "WB-STEM-08", InventoryCategory.WORKBOOKS, "Workbooks", 15, 20, 80.00, "Warehouse A - W2", "Hands-on physics and chemistry activity workbook"),

            # 3. STUDY KITS
            ("Aequs Comprehensive Student Study Kit 2026", "SK-COMP-2026", InventoryCategory.STUDY_KITS, "Kits", 65, 15, 480.00, "Warehouse B - Bay 1", "Complete kit: geometry box, 6 notebooks, pouch, scale"),
            ("Primary School Art & Craft Starter Kit", "SK-ART-PRI", InventoryCategory.STUDY_KITS, "Kits", 8, 20, 220.00, "Warehouse B - Bay 2", "Color pencils, crayons, modeling clay, and pads"),
            ("PUC Science Practical & Stationery Kit", "SK-PUC-SCI", InventoryCategory.STUDY_KITS, "Kits", 40, 10, 1150.00, "Warehouse B - Bay 3", "Lab notebooks, calculator, and drafting instruments"),

            # 4. LAPTOPS (General Inventory line)
            ("Dell Inspiron 3520 (Scholarship Batch 2024)", "LP-DEL-3520", InventoryCategory.LAPTOPS, "Units", 25, 6, 38000.00, "IT Asset Locker 1", "Core i3 12th Gen, 8GB RAM, 512GB SSD"),
            ("Lenovo V15 Laptop Power Adapters 65W", "LP-LEN-PWR", InventoryCategory.LAPTOPS, "Pieces", 4, 10, 1200.00, "IT Asset Locker 2", "Original replacement power supply adapters"),

            # 5. GOVERNMENT SCHOOL ESSENTIALS (11 Categories - Module 12)
            ("Dual-Seater Wooden Classroom Benches", "SE-BENCH-01", InventoryCategory.SCHOOL_ESSENTIALS, "Benches", 45, 10, 3200.00, "Warehouse C - Yard 1", "Sturdy hardwood dual-seater student benches with backrest"),
            ("Ergonomic Study Desks with Storage Shelf", "SE-DESK-01", InventoryCategory.SCHOOL_ESSENTIALS, "Desks", 50, 10, 2800.00, "Warehouse C - Yard 1", "Classroom study desks with bag hook and book rack"),
            ("Heavy-Duty Steel & Wooden Teacher Chairs", "SE-CHAIR-01", InventoryCategory.SCHOOL_ESSENTIALS, "Chairs", 35, 10, 1400.00, "Warehouse C - Yard 2", "Ergonomic armchairs for staff and library halls"),
            ("Magnetic Ceramic White Boards (6ft x 4ft)", "SE-WBOARD-01", InventoryCategory.SCHOOL_ESSENTIALS, "Boards", 20, 5, 2600.00, "Warehouse C - Shelf 1", "Anti-glare scratch-resistant classroom whiteboards"),
            ("School Library Reference & Encyclopedia Collection (100 Books Set)", "SE-LIB-SET", InventoryCategory.SCHOOL_ESSENTIALS, "Sets", 12, 3, 12500.00, "Warehouse C - Shelf 2", "Curated encyclopedias, biographies, and science reference books"),
            ("Physics & Chemistry Laboratory Apparatus Kit", "SE-LAB-EQ1", InventoryCategory.SCHOOL_ESSENTIALS, "Kits", 8, 3, 24000.00, "Warehouse C - Shelf 3", "Microscopes, test tubes, chemical reagents, and circuit boards"),
            ("Commercial RO+UV Water Purification Plant 50 LPH", "SE-WFILTER-01", InventoryCategory.SCHOOL_ESSENTIALS, "Units", 6, 2, 32000.00, "Warehouse C - Bay 4", "Heavy duty drinking water purification filter unit"),
            ("High-Airflow Classroom Ceiling Fans (1200mm)", "SE-FAN-01", InventoryCategory.SCHOOL_ESSENTIALS, "Units", 40, 10, 1850.00, "Warehouse C - Bay 5", "Energy efficient copper motor ceiling fans"),
            ("Comprehensive Multi-Sport Game Kit (Cricket, Football, Volleyball)", "SE-SPORT-KIT", InventoryCategory.SCHOOL_ESSENTIALS, "Kits", 15, 4, 8500.00, "Warehouse C - Bay 6", "Full outdoor sports equipment kit with inflator pump"),
            ("Smart Classroom HD Interactive Projector & Wall Screen", "SE-PROJ-01", InventoryCategory.SCHOOL_ESSENTIALS, "Sets", 5, 2, 42000.00, "Warehouse C - Secure Room", "Short-throw classroom digital projector with 100-inch screen"),
            ("3D Human Anatomy & World Geography Globes Set", "SE-EDU-RES", InventoryCategory.SCHOOL_ESSENTIALS, "Sets", 10, 3, 4500.00, "Warehouse C - Shelf 4", "Visual educational aids and tactile science models"),

            # 6. EVENT MATERIALS
            ("Annual Science Fair Exhibition Backdrops & Banners", "EM-BAN-SCI", InventoryCategory.EVENT_MATERIALS, "Rolls", 14, 4, 800.00, "Event Room 101", "Vinyl backdrop banners and welcome signage"),
            ("Annual Sports Championship Medals & Trophies Set", "EM-MED-SET", InventoryCategory.EVENT_MATERIALS, "Sets", 2, 5, 2500.00, "Event Room 101", "Gold, Silver, Bronze medals and runner-up trophies"),
            ("Portable PA Sound System & Wireless Microphones", "EM-AUD-PA1", InventoryCategory.EVENT_MATERIALS, "Sets", 5, 2, 15000.00, "AV Media Locker", "Rechargeable portable sound system for school events"),
        ]

        item_dict = {}
        for name, sku, cat, unit, stock, threshold, cost, loc, desc in inventory_items_master:
            it = InventoryItem.objects.create(
                item_name=name,
                sku=sku,
                category=cat,
                unit=unit,
                current_stock=stock,
                low_stock_threshold=threshold,
                unit_cost=Decimal(str(cost)),
                location=loc,
                description=desc,
            )
            item_dict[sku] = it

            if stock > 0:
                StockTransaction.objects.create(
                    item=it,
                    transaction_type=StockTransaction.TransactionType.STOCK_IN,
                    quantity=stock,
                    previous_stock=0,
                    new_stock=stock,
                    source_destination="Central CSR Procurement Batch 2026",
                    reference_number=f"PO-INIT-{sku}",
                    performed_by="System Admin",
                    transaction_date=timezone.localdate(),
                    notes="Initial warehouse inventory intake",
                )

        # 5. Laptops & Scholarship Assignments (Module 9)
        laptops_data = [
            ("AEQ-LP-001", "SN-DL940182", "Dell", "Inspiron 3520", 38000.00, Laptop.Condition.NEW, Laptop.Status.ISSUED),
            ("AEQ-LP-002", "SN-DL940183", "Dell", "Inspiron 3520", 38000.00, Laptop.Condition.NEW, Laptop.Status.ISSUED),
            ("AEQ-LP-003", "SN-LN773910", "Lenovo", "ThinkBook 15", 42000.00, Laptop.Condition.GOOD, Laptop.Status.ISSUED),
            ("AEQ-LP-004", "SN-HP551290", "HP", "ProBook 440", 45000.00, Laptop.Condition.GOOD, Laptop.Status.AVAILABLE),
            ("AEQ-LP-005", "SN-AC331899", "Acer", "TravelMate B3", 31000.00, Laptop.Condition.FAIR, Laptop.Status.DAMAGED),
            ("AEQ-LP-006", "SN-DL940199", "Dell", "Inspiron 3520", 38000.00, Laptop.Condition.NEW, Laptop.Status.AVAILABLE),
            ("AEQ-LP-007", "SN-LN882100", "Lenovo", "ThinkBook 15", 42000.00, Laptop.Condition.NEW, Laptop.Status.AVAILABLE),
            ("AEQ-LP-008", "SN-HP991044", "HP", "ProBook 440", 45000.00, Laptop.Condition.NEW, Laptop.Status.AVAILABLE),
        ]

        top_puc_recipients = [
            ("ADM-PUC-001", "AEQ-LP-001"),
            ("ADM-PUC-002", "AEQ-LP-002"),
            ("ADM-PUC-003", "AEQ-LP-003"),
        ]

        for asset, sn, brand, model, cost, cond, st in laptops_data:
            lap = Laptop.objects.create(
                asset_number=asset,
                serial_number=sn,
                brand=brand,
                model_name=model,
                purchase_cost=Decimal(str(cost)),
                condition=cond,
                status=st,
            )

        for adm, asset in top_puc_recipients:
            st = student_objs.get(adm)
            lap = Laptop.objects.get(asset_number=asset)
            LaptopAssignment.objects.create(
                laptop=lap,
                student=st,
                academic_year="2026-27",
                status=LaptopAssignment.Status.ISSUED,
                issue_notes="Awarded for Top PUC Academic Merit Performance",
            )
            Distribution.objects.create(
                benefit_type=BenefitType.LAPTOP,
                recipient_type=RecipientType.STUDENT,
                student=st,
                school=st.school,
                academic_year="2026-27",
                quantity=1,
                issued_by="CSR Academic Committee",
                remarks=f"Merit Scholarship Laptop #{lap.asset_number} (Rank #{AcademicRecord.objects.get(student=st).rank})",
                distribution_date=timezone.localdate(),
            )

        # 6. Sample Book Distributions (Module 6)
        book_sample_distributions = [
            ("ADM-2024-101", "BK-NCERT-M10", 1),
            ("ADM-2024-102", "BK-NCERT-M10", 1),
            ("ADM-2024-003", "BK-NCERT-S09", 1),
            ("ADM-2024-004", "BK-SOC-08", 1),
        ]
        for adm, sku, qty in book_sample_distributions:
            st = student_objs.get(adm)
            it = item_dict.get(sku)
            if st and it and it.current_stock >= qty:
                it.current_stock -= qty
                it.save()
                Distribution.objects.create(
                    benefit_type=BenefitType.BOOK,
                    recipient_type=RecipientType.STUDENT,
                    student=st,
                    school=st.school,
                    inventory_item=it,
                    academic_year="2026-27",
                    quantity=qty,
                    issued_by="School Coordinator",
                    remarks=f"Class syllabus textbook distribution ({it.item_name})",
                    distribution_date=timezone.localdate(),
                )
                StockTransaction.objects.create(
                    item=it,
                    transaction_type=StockTransaction.TransactionType.STOCK_OUT,
                    quantity=qty,
                    previous_stock=it.current_stock + qty,
                    new_stock=it.current_stock,
                    source_destination=f"Student: {st.student_name} ({st.current_class})",
                    reference_number=f"DIST-BK-{st.admission_number}",
                    performed_by="School Coordinator",
                    transaction_date=timezone.localdate(),
                    notes="Book Distribution",
                )

        # 7. Sample Workbook Distributions (Module 7)
        workbook_sample_distributions = [
            ("ADM-2024-101", "WB-SCI-10", 1),
            ("ADM-2024-102", "WB-SCI-10", 1),
            ("ADM-2024-104", "WB-MATH-10", 1),
        ]
        for adm, sku, qty in workbook_sample_distributions:
            st = student_objs.get(adm)
            it = item_dict.get(sku)
            if st and it and it.current_stock >= qty:
                it.current_stock -= qty
                it.save()
                Distribution.objects.create(
                    benefit_type=BenefitType.WORKBOOK,
                    recipient_type=RecipientType.STUDENT,
                    student=st,
                    school=st.school,
                    inventory_item=it,
                    academic_year="2026-27",
                    quantity=qty,
                    issued_by="Academic Faculty",
                    remarks="Class 10 Board exam workbook distribution",
                    distribution_date=timezone.localdate(),
                )
                StockTransaction.objects.create(
                    item=it,
                    transaction_type=StockTransaction.TransactionType.STOCK_OUT,
                    quantity=qty,
                    previous_stock=it.current_stock + qty,
                    new_stock=it.current_stock,
                    source_destination=f"Class 10 Student: {st.student_name}",
                    reference_number=f"DIST-WB-{st.admission_number}",
                    performed_by="Academic Faculty",
                    transaction_date=timezone.localdate(),
                    notes="Class 10 Workbook Distribution",
                )

        # 8. Sample Study Kit Distributions (Module 8)
        kit_sample_distributions = [
            ("ADM-2024-005", "SK-COMP-2026", kit2, 1),
            ("ADM-2024-007", "SK-ART-PRI", kit1, 1),
            ("ADM-PUC-004", "SK-PUC-SCI", kit3, 1),
            ("ADM-PUC-005", "SK-PUC-SCI", kit3, 1),
        ]
        for adm, sku, k_obj, qty in kit_sample_distributions:
            st = student_objs.get(adm)
            it = item_dict.get(sku)
            if st and it and it.current_stock >= qty:
                it.current_stock -= qty
                it.save()
                Distribution.objects.create(
                    benefit_type=BenefitType.STUDY_KIT,
                    recipient_type=RecipientType.STUDENT,
                    student=st,
                    school=st.school,
                    inventory_item=it,
                    study_kit=k_obj,
                    academic_year="2026-27",
                    quantity=qty,
                    issued_by="CSR Volunteer",
                    remarks=f"Study Kit issuance: {k_obj.name}",
                    distribution_date=timezone.localdate(),
                )
                StockTransaction.objects.create(
                    item=it,
                    transaction_type=StockTransaction.TransactionType.STOCK_OUT,
                    quantity=qty,
                    previous_stock=it.current_stock + qty,
                    new_stock=it.current_stock,
                    source_destination=f"Student Study Kit: {st.student_name} ({st.current_class})",
                    reference_number=f"DIST-SK-{st.admission_number}",
                    performed_by="CSR Volunteer",
                    transaction_date=timezone.localdate(),
                    notes="Study Kit Distribution",
                )

        # 9. Sample Government School Essentials Distributions (Module 12)
        school_essentials_dispatches = [
            (main_school, "SE-BENCH-01", SchoolEssentialType.BENCHES, 15, "Classroom Block A Infrastructure Upgrade"),
            (main_school, "SE-WBOARD-01", SchoolEssentialType.WHITE_BOARDS, 4, "Smart Classrooms 6-10"),
            (main_school, "SE-WFILTER-01", SchoolEssentialType.WATER_FILTERS, 1, "Drinking water facility"),
            (created_schools[2], "SE-DESK-01", SchoolEssentialType.DESKS, 20, "Middle School Desk Allocation"),
            (created_schools[2], "SE-SPORT-KIT", SchoolEssentialType.SPORTS_KITS, 2, "Sports Day Equipment"),
            (puc_college, "SE-LAB-EQ1", SchoolEssentialType.LAB_EQUIPMENT, 2, "Physics and Chemistry Lab setup"),
            (puc_college, "SE-PROJ-01", SchoolEssentialType.PROJECTORS, 2, "Seminar Hall & Audio Visual Room"),
        ]

        for sch, sku, ess_type, qty, rem in school_essentials_dispatches:
            it = item_dict.get(sku)
            if sch and it and it.current_stock >= qty:
                it.current_stock -= qty
                it.save()
                Distribution.objects.create(
                    benefit_type=BenefitType.SCHOOL_ESSENTIAL,
                    recipient_type=RecipientType.SCHOOL,
                    school=sch,
                    inventory_item=it,
                    essential_item_type=ess_type,
                    academic_year="2026-27",
                    quantity=qty,
                    issued_by="Logistics Coordinator",
                    remarks=rem,
                    distribution_date=timezone.localdate(),
                )
                StockTransaction.objects.create(
                    item=it,
                    transaction_type=StockTransaction.TransactionType.STOCK_OUT,
                    quantity=qty,
                    previous_stock=it.current_stock + qty,
                    new_stock=it.current_stock,
                    source_destination=f"School: {sch.name} (UDISE: {sch.udise_code})",
                    reference_number=f"DSP-SCH-{sch.udise_code}",
                    performed_by="Logistics Coordinator",
                    transaction_date=timezone.localdate(),
                    notes=f"Government School Essential ({ess_type}): {rem}",
                )
                # Update / Create SchoolResource
                SchoolResource.objects.create(
                    school=sch,
                    resource_name=it.item_name,
                    quantity=qty,
                    status="Delivered",
                    last_updated_note=f"Dispatched +{qty} {it.unit} on {timezone.localdate().strftime('%Y-%m-%d')}",
                    details=f"Essential category: {ess_type}. {rem}",
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded comprehensive data:\n"
                f"  - {len(inventory_items_master)} Inventory Items (including 11 School Essentials)\n"
                f"  - {len(students_dataset)} Students (Class 1-10 + Top PUC Merit Candidates)\n"
                f"  - {len(created_schools)} Government Schools\n"
                f"  - 3 Configurable Study Kits with Sub-items\n"
                f"  - {len(laptops_data)} Laptops & Assignments\n"
                f"  - {Distribution.objects.count()} Distribution Records synchronized with Inventory!"
            )
        )
