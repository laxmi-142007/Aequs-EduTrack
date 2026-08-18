from django.test import TestCase

from schools.models import School
from students.models import Student
from academics.models import AcademicRecord
from eligibility.models import EligibilityRecord, BenefitType
from eligibility import services


class EligibilityServiceTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            udise_code="TEST001",
            address="Test Address",
            district="Test District",
            headmaster_name="Test Headmaster",
        )

        self.student = Student.objects.create(
            student_name="Test Student",
            admission_number="TEST001",
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

    def create_academic_record(
        self,
        class_or_course,
        percentage=95,
        academic_year="2026-27",
    ):
        return AcademicRecord.objects.create(
            student=self.student,
            academic_year=academic_year,
            class_or_course=class_or_course,
            percentage=percentage,
        )

    def test_school_class_detection(self):
        self.assertEqual(
            services.is_school_class("Class 10"),
            10,
        )

    def test_second_puc_detection(self):
        self.assertTrue(
            services.is_second_puc("2nd PUC")
        )

    def test_be_second_year_detection(self):
        self.assertTrue(
            services.is_be_second_year("BE 2nd Year")
        )

    def test_degree_first_year_detection(self):
        self.assertTrue(
            services.is_degree_first_year("Degree 1st Year")
        )

    def test_final_year_diploma_detection(self):
        record = self.create_academic_record(
            "Diploma 3rd Year"
        )

        self.assertTrue(
            services.is_final_year_diploma(record)
        )

    def test_non_final_year_diploma_detection(self):
        record = self.create_academic_record(
            "Diploma 2nd Year"
        )

        self.assertFalse(
            services.is_final_year_diploma(record)
        )

    def test_book_eligibility_for_class_10(self):
        record = self.create_academic_record("Class 10")

        result = services.generate_book_eligibility(
            self.student,
            record,
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.eligible)

    def test_book_eligibility_for_class_5(self):
        record = self.create_academic_record("Class 5")

        result = services.generate_book_eligibility(
            self.student,
            record,
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.eligible)

    def test_book_not_given_for_puc(self):
        record = self.create_academic_record("2nd PUC")

        result = services.generate_book_eligibility(
            self.student,
            record,
        )

        self.assertIsNone(result)

    def test_workbook_eligibility_only_class_10(self):
        record = self.create_academic_record("Class 10")

        result = services.generate_workbook_eligibility(
            self.student,
            record,
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.eligible)

    def test_workbook_not_for_class_9(self):
        record = self.create_academic_record("Class 9")

        result = services.generate_workbook_eligibility(
            self.student,
            record,
        )

        self.assertIsNone(result)

    def test_second_puc_student_can_get_laptop(self):
        record = self.create_academic_record(
            "2nd PUC",
            percentage=95,
        )

        result = services.get_laptop_qualifying_students(
            "2026-27"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].student, self.student)

    def test_final_year_diploma_student_can_get_laptop(self):
        record = self.create_academic_record(
            "Diploma 3rd Year",
            percentage=95,
        )

        result = services.get_laptop_qualifying_students(
            "2026-27"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].student, self.student)

    def test_laptop_distribution_requires_previous_selection(self):
        record = self.create_academic_record(
            "Degree 1st Year"
        )

        result = services.generate_laptop_distribution_eligibility(
            self.student,
            record,
        )

        self.assertIsNone(result)

    def test_laptop_distribution_after_previous_selection(self):
        EligibilityRecord.objects.create(
            student=self.student,
            benefit_type=BenefitType.LAPTOP,
            academic_year="2025-26",
            eligible=True,
            selection_rank=1,
        )

        record = self.create_academic_record(
            "Degree 1st Year",
            academic_year="2026-27",
        )

        result = services.generate_laptop_distribution_eligibility(
            self.student,
            record,
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.eligible)

    def test_top_class_10_student_gets_study_kit(self):
        self.create_academic_record(
            "Class 10",
            percentage=95,
        )

        services.generate_study_kit_eligibility(
            "2026-27"
        )

        result = EligibilityRecord.objects.filter(
            student=self.student,
            benefit_type=BenefitType.STUDY_KIT,
            academic_year="2026-27",
            eligible=True,
        )

        self.assertTrue(result.exists())
