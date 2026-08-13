import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError

from distributions.models import (
    Distribution,
    BenefitType,
    RecipientType,
    SchoolEssentialType,
    StudyKit,
    StudyKitItem,
)
from distributions.services import (
    distribute_books,
    distribute_workbooks,
    issue_study_kit,
    issue_laptop_scholarship,
    distribute_school_essentials,
    get_top_puc_students,
    get_eligible_students_for_benefit,
)
from students.models import Student
from schools.models import School, SchoolResource
from academics.models import AcademicRecord
from inventory.models import InventoryItem, InventoryCategory, Laptop, LaptopAssignment, StockTransaction


class DistributionServicesAndRulesTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Govt. Model High School",
            udise_code="29010200301",
            district="Bangalore Urban",
        )
        self.student_class_8 = Student.objects.create(
            student_name="Kavya Reddy",
            admission_number="ADM-C8-01",
            school=self.school,
            current_class="Class 8",
        )
        self.student_class_10 = Student.objects.create(
            student_name="Aarav Sharma",
            admission_number="ADM-C10-01",
            school=self.school,
            current_class="Class 10",
        )
        self.student_puc = Student.objects.create(
            student_name="Aditi Hegde",
            admission_number="ADM-PUC-01",
            school=self.school,
            current_class="2nd PUC",
        )

        AcademicRecord.objects.create(
            student=self.student_puc,
            academic_year="2024-2025",
            class_or_course="2nd PUC",
            percentage=Decimal("96.50"),
            rank=1,
            promotion_status="Promoted",
        )

        self.book_item = InventoryItem.objects.create(
            item_name="Class 8 Social Science Book",
            sku="BK-SOC-08",
            category=InventoryCategory.BOOKS,
            current_stock=20,
            low_stock_threshold=5,
            unit="Copies",
        )
        self.wb_item = InventoryItem.objects.create(
            item_name="Class 10 Science Practice Workbook",
            sku="WB-SCI-10",
            category=InventoryCategory.WORKBOOKS,
            current_stock=15,
            low_stock_threshold=5,
            unit="Workbooks",
        )
        self.bench_item = InventoryItem.objects.create(
            item_name="Dual Seater Classroom Benches",
            sku="SE-BENCH-01",
            category=InventoryCategory.SCHOOL_ESSENTIALS,
            current_stock=10,
            low_stock_threshold=2,
            unit="Benches",
        )
        self.laptop = Laptop.objects.create(
            asset_number="AEQ-LP-TEST1",
            serial_number="SN-TEST-001",
            brand="Dell",
            model_name="Inspiron 3520",
            status=Laptop.Status.AVAILABLE,
        )

    def test_book_distribution_eligibility_and_stock_sync(self):
        # Class 8 is eligible for Books
        prev_stock = self.book_item.current_stock
        dist = distribute_books(
            student=self.student_class_8,
            item=self.book_item,
            quantity=2,
            academic_year="2026-27",
            issued_by="Teacher",
        )
        self.book_item.refresh_from_db()
        self.assertEqual(self.book_item.current_stock, prev_stock - 2)
        self.assertEqual(dist.benefit_type, BenefitType.BOOK)
        self.assertEqual(dist.quantity, 2)

        # Non-Class 1-10 student (e.g. PUC) cannot receive Class 1-10 syllabus book
        with self.assertRaises(ValidationError):
            distribute_books(
                student=self.student_puc,
                item=self.book_item,
                quantity=1,
            )

    def test_workbook_distribution_class_10_strict_eligibility(self):
        # Class 10 student can receive workbook
        prev_stock = self.wb_item.current_stock
        dist = distribute_workbooks(
            student=self.student_class_10,
            item=self.wb_item,
            quantity=1,
            academic_year="2026-27",
        )
        self.wb_item.refresh_from_db()
        self.assertEqual(self.wb_item.current_stock, prev_stock - 1)
        self.assertEqual(dist.benefit_type, BenefitType.WORKBOOK)

        # Class 8 student cannot receive Class 10 workbook
        with self.assertRaises(ValidationError):
            distribute_workbooks(
                student=self.student_class_8,
                item=self.wb_item,
                quantity=1,
            )

    def test_study_kit_issuance_up_to_2nd_puc(self):
        kit = StudyKit.objects.create(
            name="PUC Science Practical Kit",
            target_grade_level="1st & 2nd PUC",
        )
        dist = issue_study_kit(
            student=self.student_puc,
            kit=kit,
            quantity=1,
            academic_year="2026-27",
        )
        self.assertEqual(dist.benefit_type, BenefitType.STUDY_KIT)
        self.assertEqual(dist.study_kit, kit)

    def test_laptop_scholarship_and_top_puc_selection(self):
        top_students = get_top_puc_students(limit=10)
        self.assertEqual(len(top_students), 1)
        self.assertEqual(top_students[0]["student_name"], "Aditi Hegde")
        self.assertEqual(top_students[0]["percentage"], 96.5)
        self.assertFalse(top_students[0]["has_laptop"])

        # Award laptop
        assignment, dist = issue_laptop_scholarship(
            student=self.student_puc,
            laptop=self.laptop,
            academic_year="2026-27",
            notes="Merit Award Rank #1",
        )
        self.laptop.refresh_from_db()
        self.assertEqual(self.laptop.status, Laptop.Status.ISSUED)
        self.assertEqual(dist.benefit_type, BenefitType.LAPTOP)

    def test_school_essentials_distribution_and_inventory_sync(self):
        prev_stock = self.bench_item.current_stock
        dist = distribute_school_essentials(
            school=self.school,
            item=self.bench_item,
            essential_type=SchoolEssentialType.BENCHES,
            quantity=4,
            academic_year="2026-27",
            remarks="Classroom upgrade",
        )
        self.bench_item.refresh_from_db()
        self.assertEqual(self.bench_item.current_stock, prev_stock - 4)
        self.assertEqual(dist.benefit_type, BenefitType.SCHOOL_ESSENTIAL)
        self.assertEqual(dist.recipient_type, RecipientType.SCHOOL)

        # Cross-portal check: SchoolResource created
        res = SchoolResource.objects.filter(school=self.school, resource_name=self.bench_item.item_name).first()
        self.assertIsNotNone(res)
        self.assertEqual(res.quantity, 4)


class DistributionAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Govt. Model High School",
            udise_code="29010200301",
            district="Bangalore Urban",
        )
        self.student = Student.objects.create(
            student_name="Diya Patel",
            admission_number="ADM-API-01",
            school=self.school,
            current_class="Class 10",
        )
        self.book = InventoryItem.objects.create(
            item_name="NCERT Math Class 10",
            sku="BK-M10",
            category=InventoryCategory.BOOKS,
            current_stock=25,
            unit="Copies",
        )
        self.wb = InventoryItem.objects.create(
            item_name="Math Workbook Class 10",
            sku="WB-M10",
            category=InventoryCategory.WORKBOOKS,
            current_stock=20,
            unit="Workbooks",
        )
        self.bench = InventoryItem.objects.create(
            item_name="Benches Wooden",
            sku="SE-BENCH-API",
            category=InventoryCategory.SCHOOL_ESSENTIALS,
            current_stock=10,
            unit="Benches",
        )

    def test_api_eligible_students(self):
        res = self.client.get(reverse("distributions:api_eligible_students") + "?benefit_type=WORKBOOK")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["students"]), 1)

    def test_api_distribute_book(self):
        payload = {
            "student_id": self.student.id,
            "item_id": self.book.id,
            "quantity": 1,
            "academic_year": "2026-27",
        }
        res = self.client.post(
            reverse("distributions:api_distribute_book"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])
        self.book.refresh_from_db()
        self.assertEqual(self.book.current_stock, 24)

    def test_api_distribute_workbook(self):
        payload = {
            "student_id": self.student.id,
            "item_id": self.wb.id,
            "quantity": 1,
        }
        res = self.client.post(
            reverse("distributions:api_distribute_workbook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

    def test_api_distribute_school_essentials(self):
        payload = {
            "school_id": self.school.id,
            "item_id": self.bench.id,
            "essential_type": "BENCHES",
            "quantity": 3,
        }
        res = self.client.post(
            reverse("distributions:api_distribute_school_essentials"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])
        self.bench.refresh_from_db()
        self.assertEqual(self.bench.current_stock, 7)

    def test_distribution_create_view(self):
        # GET form
        res_get = self.client.get(reverse("distributions:create"))
        self.assertEqual(res_get.status_code, 200)
        self.assertContains(res_get, "Add New Distribution")

        # POST form
        post_data = {
            "benefit_type": "BOOK",
            "student": self.student.id,
            "inventory_item": self.book.id,
            "academic_year": "2026-27",
            "quantity": 2,
            "issued_by": "Coordinator",
            "remarks": "Issued via standard form",
        }
        res_post = self.client.post(reverse("distributions:create"), data=post_data)
        self.assertEqual(res_post.status_code, 302)
        self.assertRedirects(res_post, reverse("distributions:list"))

        # Check distribution created
        dist = Distribution.objects.filter(student=self.student, benefit_type="BOOK").first()
        self.assertIsNotNone(dist)
        self.assertEqual(dist.quantity, 2)
        self.assertEqual(dist.issued_by, "Coordinator")
