from django.test import TestCase

from schools.models import School
from students.models import Student
from eligibility.models import EligibilityRecord, BenefitType
from distributions.models import Distribution
from distributions.forms import DistributionForm


class DistributionFormTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            udise_code="DIST001",
            address="Test Address",
            district="Test District",
            headmaster_name="Test Headmaster",
        )

        self.student = Student.objects.create(
            student_name="Distribution Student",
            admission_number="DIST001",
            school=self.school,
            gender=Student.Gender.MALE,
            current_class="10",
            section="A",
            roll_number="1",
            parent_name="Test Parent",
            parent_phone="9999999999",
            parent_email="parent@test.com",
            student_phone="9999999999",
            email="student@test.com",
            address="Test Address",
        )

    def create_eligibility(self):
        return EligibilityRecord.objects.create(
            student=self.student,
            benefit_type=BenefitType.BOOK,
            academic_year="2026-27",
            eligible=True,
        )

    def test_eligible_student_can_create_distribution(self):
        self.create_eligibility()

        form = DistributionForm(
            data={
                "student": self.student.id,
                "benefit_type": "BOOK",
                "academic_year": "2026-27",
                "quantity": 1,
                "issued_by": "Test Staff",
                "remarks": "",
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_ineligible_student_cannot_create_distribution(self):
        form = DistributionForm(
            data={
                "student": self.student.id,
                "benefit_type": "BOOK",
                "academic_year": "2026-27",
                "quantity": 1,
                "issued_by": "Test Staff",
                "remarks": "",
            }
        )

        self.assertFalse(form.is_valid())

    def test_duplicate_distribution_is_rejected(self):
        self.create_eligibility()

        Distribution.objects.create(
            student=self.student,
            benefit_type=BenefitType.BOOK,
            academic_year="2026-27",
            quantity=1,
        )

        form = DistributionForm(
            data={
                "student": self.student.id,
                "benefit_type": "BOOK",
                "academic_year": "2026-27",
                "quantity": 1,
                "issued_by": "Test Staff",
                "remarks": "",
            }
        )

        self.assertFalse(form.is_valid())
