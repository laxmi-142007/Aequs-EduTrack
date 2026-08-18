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
