import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError

from inventory.models import (
    InventoryCategory,
    InventoryItem,
    StockTransaction,
    Laptop,
    LaptopAssignment,
)
from inventory.services import (
    process_stock_in,
    process_stock_out,
    adjust_stock,
    issue_laptop,
    return_laptop,
)
from schools.models import School
from students.models import Student


class InventoryModelAndServiceTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Govt. Model High School",
            udise_code="29010200301",
            district="Bangalore Urban",
        )
        self.student = Student.objects.create(
            student_name="Rahul Kumar",
            admission_number="ADM-TEST-001",
            school=self.school,
            current_class="Class 10",
        )

        self.book_item = InventoryItem.objects.create(
            item_name="Class 10 Science Textbook",
            sku="BK-SCI-10",
            category=InventoryCategory.BOOKS,
            unit="Copies",
            current_stock=50,
            low_stock_threshold=15,
            unit_cost=Decimal("150.00"),
            location="Rack B1",
        )

    def test_item_categories_and_stock_properties(self):
        self.assertEqual(self.book_item.category, InventoryCategory.BOOKS)
        self.assertFalse(self.book_item.is_low_stock)
        self.assertEqual(self.book_item.stock_status, "IN_STOCK")

        # Test low stock threshold
        self.book_item.current_stock = 10
        self.book_item.save()
        self.assertTrue(self.book_item.is_low_stock)
        self.assertEqual(self.book_item.stock_status, "LOW_STOCK")

        # Test out of stock
        self.book_item.current_stock = 0
        self.book_item.save()
        self.assertTrue(self.book_item.is_low_stock)
        self.assertEqual(self.book_item.stock_status, "OUT_OF_STOCK")

    def test_stock_in_service(self):
        prev = self.book_item.current_stock
        tx = process_stock_in(
            item=self.book_item,
            quantity=25,
            source_destination="Publisher Warehouse",
            reference_number="PO-1001",
            performed_by="Admin",
            notes="Bulk intake",
        )

        self.book_item.refresh_from_db()
        self.assertEqual(self.book_item.current_stock, prev + 25)
        self.assertEqual(tx.previous_stock, prev)
        self.assertEqual(tx.new_stock, prev + 25)
        self.assertEqual(tx.transaction_type, StockTransaction.TransactionType.STOCK_IN)

    def test_stock_out_service(self):
        prev = self.book_item.current_stock
        tx = process_stock_out(
            item=self.book_item,
            quantity=15,
            source_destination="Govt School Jayanagar",
            reference_number="DSP-101",
            performed_by="Logistics Coordinator",
        )

        self.book_item.refresh_from_db()
        self.assertEqual(self.book_item.current_stock, prev - 15)
        self.assertEqual(tx.previous_stock, prev)
        self.assertEqual(tx.new_stock, prev - 15)
        self.assertEqual(tx.transaction_type, StockTransaction.TransactionType.STOCK_OUT)

    def test_stock_out_insufficient_stock_error(self):
        with self.assertRaises(ValidationError):
            process_stock_out(
                item=self.book_item,
                quantity=self.book_item.current_stock + 100,
                source_destination="Test Dest",
            )

    def test_adjust_stock_service(self):
        tx = adjust_stock(
            item=self.book_item,
            new_quantity=30,
            reason="Physical inventory audit reconciliation",
            performed_by="Auditor",
        )
        self.book_item.refresh_from_db()
        self.assertEqual(self.book_item.current_stock, 30)
        self.assertIsNotNone(tx)
        self.assertEqual(tx.transaction_type, StockTransaction.TransactionType.ADJUSTMENT)

    def test_laptop_issue_and_return_workflow(self):
        laptop = Laptop.objects.create(
            asset_number="AEQ-LP-TEST",
            serial_number="SN-TEST-88",
            brand="Dell",
            model_name="Inspiron 3520",
            status=Laptop.Status.AVAILABLE,
        )

        assignment = issue_laptop(
            student=self.student,
            laptop=laptop,
            academic_year="2026-27",
            bypass_eligibility=True,
        )

        laptop.refresh_from_db()
        self.assertEqual(laptop.status, Laptop.Status.ISSUED)
        self.assertEqual(assignment.status, LaptopAssignment.Status.ISSUED)

        # Return laptop
        return_laptop(assignment, return_notes="Returned in good shape")
        laptop.refresh_from_db()
        assignment.refresh_from_db()
        self.assertEqual(laptop.status, Laptop.Status.AVAILABLE)
        self.assertEqual(assignment.status, LaptopAssignment.Status.RETURNED)


class InventoryAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Govt. Model High School",
            udise_code="29010200301",
            district="Bangalore Urban",
        )
        self.student = Student.objects.create(
            student_name="Ananya Rao",
            admission_number="ADM-TEST-002",
            school=self.school,
            current_class="Class 9",
        )
        self.item = InventoryItem.objects.create(
            item_name="STEM Robotics Kit",
            sku="SK-ROB-01",
            category=InventoryCategory.STUDY_KITS,
            unit="Kits",
            current_stock=5,
            low_stock_threshold=10,
            unit_cost=Decimal("1200.00"),
        )

    def test_portal_view(self):
        response = self.client.get(reverse("inventory:portal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventory Management")

    def test_api_inventory_items(self):
        response = self.client.get(reverse("inventory:api_items"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["items"]), 1)

    def test_api_create_inventory_item(self):
        payload = {
            "item_name": "Annual Sports Banners",
            "sku": "EM-BAN-01",
            "category": "EVENT_MATERIALS",
            "unit": "Rolls",
            "initial_stock": 10,
            "low_stock_threshold": 3,
            "unit_cost": 500.0,
            "location": "Event Room",
        }
        response = self.client.post(
            reverse("inventory:api_create_item"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["item"]["sku"], "EM-BAN-01")

    def test_api_stock_in(self):
        payload = {
            "item_id": self.item.id,
            "quantity": 20,
            "source": "Vendor Supplier",
            "reference_number": "PO-9901",
        }
        response = self.client.post(
            reverse("inventory:api_stock_in"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["item"]["current_stock"], 25)

    def test_api_stock_out(self):
        payload = {
            "item_id": self.item.id,
            "quantity": 3,
            "destination": "High School Science Lab",
            "reference_number": "DSP-882",
        }
        response = self.client.post(
            reverse("inventory:api_stock_out"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["item"]["current_stock"], 2)

    def test_api_low_stock_alerts(self):
        response = self.client.get(reverse("inventory:api_low_stock_alerts"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        # self.item has stock=5 and threshold=10, so it must be in low stock alerts
        self.assertTrue(any(i["id"] == self.item.id for i in data["alerts"]))

    def test_api_laptops_and_issue_return(self):
        laptop = Laptop.objects.create(
            asset_number="AEQ-LP-API",
            serial_number="SN-API-999",
            brand="Lenovo",
            model_name="ThinkBook 15",
            status=Laptop.Status.AVAILABLE,
        )

        # Issue
        issue_payload = {
            "laptop_id": laptop.id,
            "student_id": self.student.id,
            "academic_year": "2026-27",
            "notes": "Issued via API",
        }
        issue_res = self.client.post(
            reverse("inventory:api_issue_laptop"),
            data=json.dumps(issue_payload),
            content_type="application/json",
        )
        self.assertEqual(issue_res.status_code, 200)
        self.assertTrue(issue_res.json()["success"])

        # Return
        return_res = self.client.post(
            reverse("inventory:api_return_laptop", args=[laptop.id]),
            data=json.dumps({"return_notes": "Returned API test"}),
            content_type="application/json",
        )
        self.assertEqual(return_res.status_code, 200)
        self.assertTrue(return_res.json()["success"])

    def test_export_csv(self):
        response = self.client.get(reverse("inventory:export_csv") + "?type=items")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Item Name", response.content.decode("utf-8"))
from django.test import TestCase
from django.core.exceptions import ValidationError

from schools.models import School
from students.models import Student
from eligibility.models import EligibilityRecord, BenefitType

from inventory.models import Laptop, LaptopAssignment
from inventory.services import (
    issue_laptop,
    return_laptop,
    replace_laptop,
)


class LaptopServiceTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            udise_code="LAP001",
            address="Test Address",
            district="Test District",
            headmaster_name="Test Headmaster",
        )

        self.student = Student.objects.create(
            student_name="Laptop Student",
            admission_number="LAP001",
            school=self.school,
            gender=Student.Gender.MALE,
            current_class="2nd PUC",
            section="A",
            roll_number="1",
            parent_name="Test Parent",
            parent_phone="9999999999",
            parent_email="parent@test.com",
            student_phone="9999999999",
            email="student@test.com",
            address="Test Address",
        )

        self.laptop = Laptop.objects.create(
            asset_number="ASSET001",
            serial_number="SERIAL001",
            brand="TestBrand",
            model_name="TestModel",
        )

        EligibilityRecord.objects.create(
            student=self.student,
            benefit_type=BenefitType.LAPTOP,
            academic_year="2026-27",
            eligible=True,
        )

    def test_issue_laptop_to_eligible_student(self):
        assignment = issue_laptop(
            self.student,
            self.laptop,
            "2026-27",
        )

        self.assertIsNotNone(assignment)
        self.assertEqual(
            assignment.status,
            LaptopAssignment.Status.ISSUED,
        )

        self.laptop.refresh_from_db()

        self.assertEqual(
            self.laptop.status,
            Laptop.Status.ISSUED,
        )

    def test_cannot_issue_unavailable_laptop(self):
        self.laptop.status = Laptop.Status.ISSUED
        self.laptop.save()

        with self.assertRaises(ValidationError):
            issue_laptop(
                self.student,
                self.laptop,
                "2026-27",
            )

    def test_return_laptop(self):
        assignment = issue_laptop(
            self.student,
            self.laptop,
            "2026-27",
        )

        return_laptop(
            assignment,
            "Returned normally",
        )

        assignment.refresh_from_db()
        self.laptop.refresh_from_db()

        self.assertEqual(
            assignment.status,
            LaptopAssignment.Status.RETURNED,
        )

        self.assertEqual(
            self.laptop.status,
            Laptop.Status.AVAILABLE,
        )

    def test_cannot_issue_second_laptop_to_same_student(self):
        second_laptop = Laptop.objects.create(
            asset_number="ASSET002",
            serial_number="SERIAL002",
            brand="TestBrand",
            model_name="TestModel",
        )

        issue_laptop(
            self.student,
            self.laptop,
            "2026-27",
        )

        with self.assertRaises(ValidationError):
            issue_laptop(
                self.student,
                second_laptop,
                "2026-27",
            )

    def test_replace_laptop(self):
        assignment = issue_laptop(
            self.student,
            self.laptop,
            "2026-27",
        )

        replacement = Laptop.objects.create(
            asset_number="ASSET002",
            serial_number="SERIAL002",
            brand="ReplacementBrand",
            model_name="ReplacementModel",
        )

        new_assignment = replace_laptop(
            assignment,
            replacement,
            "Damaged laptop",
        )

        assignment.refresh_from_db()
        self.laptop.refresh_from_db()
        replacement.refresh_from_db()

        self.assertEqual(
            assignment.status,
            LaptopAssignment.Status.REPLACED,
        )

        self.assertEqual(
            self.laptop.status,
            Laptop.Status.REPLACED,
        )

        self.assertEqual(
            new_assignment.status,
            LaptopAssignment.Status.ISSUED,
        )

        self.assertEqual(
            replacement.status,
            Laptop.Status.ISSUED,
        )
