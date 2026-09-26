from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from schools.models import School
from students.models import Student
from academics.models import AcademicRecord
from eligibility.models import EligibilityRecord, BenefitType as EligBenefitType
from distributions.models import Distribution, BenefitType as DistBenefitType, StudyKit
from internships.models import InternshipProgram, InternshipPlacement, Department


class StudentModuleTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.school = School.objects.create(
            name="Aequs Partner Govt High School",
            udise_code="29010200501",
            district="Belagavi",
            taluk="Hukkeri",
            village="Hattargi",
        )

        self.student = Student.objects.create(
            admission_number="AEQ-STU-101",
            student_name="Priya Patil",
            date_of_birth="2010-05-15",
            gender=Student.Gender.FEMALE,
            school=self.school,
            current_class="10",
            section="A",
            roll_number="12",
            parent_name="Suresh Patil",
            parent_phone="9876543210",
            parent_email="suresh.patil@example.com",
            relationship_to_student="Father",
            student_phone="9876543211",
            address="Hattargi Village, Belagavi",
            status=Student.Status.ACTIVE,
        )

        # Related academic record
        self.academic_rec = AcademicRecord.objects.create(
            student=self.student,
            academic_year="2025-26",
            class_or_course="10",
            marks_obtained=Decimal("540.00"),
            total_marks=Decimal("600.00"),
            percentage=Decimal("90.00"),
            rank=1,
            promotion_status="Promoted",
            remarks="Excellent academic performance",
        )

        # Related eligibility record (signal may have auto-generated it on AcademicRecord save)
        self.elig_rec, _ = EligibilityRecord.objects.get_or_create(
            student=self.student,
            benefit_type=EligBenefitType.STUDY_KIT,
            academic_year="2025-26",
            defaults={
                "eligible": True,
                "selection_rank": 1,
                "reason": "High merit score in Class 9",
            },
        )

        # Related study kit & distribution
        self.kit = StudyKit.objects.create(
            name="High School STEM Kit",
            target_grade_level="Class 10",
            description="Geometry box, science project kit, notebooks",
        )
        self.dist = Distribution.objects.create(
            benefit_type=DistBenefitType.STUDY_KIT,
            student=self.student,
            school=self.school,
            study_kit=self.kit,
            quantity=1,
            remarks="Handed over during annual school drive",
        )

        # Related internship
        self.program = InternshipProgram.objects.create(
            title="Aequs Aerospace Metrology Track",
            program_code="AEQ-MET-01",
            company_name="Aequs Precision Engineering",
            department=Department.QUALITY_ASSURANCE,
        )
        self.placement = InternshipPlacement.objects.create(
            student=self.student,
            program=self.program,
            status=InternshipPlacement.Status.SELECTED,
            performance_grade=InternshipPlacement.PerformanceGrade.OUTSTANDING,
        )

    def test_student_list_view_loads_successfully(self):
        url = reverse("students:list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_list.html")
        content = response.content.decode("utf-8")
        self.assertIn("Aequs-logo.png", content)
        self.assertIn("Student Directory", content)

    def test_student_detail_view_loads_successfully(self):
        url = reverse("students:detail", args=[self.student.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_detail.html")
        self.assertEqual(response.context["student"], self.student)

        # Check related records in context
        self.assertIn(self.academic_rec, response.context["academic_records"])
        self.assertIn(self.elig_rec, response.context["eligibility_records"])
        self.assertIn(self.dist, response.context["distributions"])
        self.assertIn(self.placement, response.context["internships"])

        # Check HTML contains student information & AF branding
        content = response.content.decode("utf-8")
        self.assertIn("Priya Patil", content)
        self.assertIn("AEQ-STU-101", content)
        self.assertIn("Aequs-logo.png", content)
        self.assertIn("Student ID Card", content)
        self.assertIn("Edit Profile", content)

    def test_student_detail_nonexistent_returns_404(self):
        url = reverse("students:detail", args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_edit_student_get_view(self):
        url = reverse("students:edit", args=[self.student.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/add_student.html")
        self.assertTrue(response.context["is_edit"])
        self.assertEqual(response.context["student"], self.student)

        content = response.content.decode("utf-8")
        self.assertIn("Edit Student Profile", content)
        self.assertIn("Save Changes", content)

    def test_edit_student_post_updates_record(self):
        url = reverse("students:edit", args=[self.student.pk])
        post_data = {
            "admission_number": "AEQ-STU-101",
            "student_name": "Priya S. Patil",
            "school": self.school.pk,
            "current_class": "10",
            "section": "B",
            "roll_number": "15",
            "gender": "FEMALE",
            "parent_name": "Suresh Patil",
            "parent_phone": "9998887776",
            "parent_email": "suresh@example.com",
            "relationship_to_student": "Father",
            "student_phone": "9876543211",
            "address": "Updated Village Address",
            "status": "ACTIVE",
        }

        response = self.client.post(url, post_data)
        self.assertRedirects(response, reverse("students:detail", args=[self.student.pk]))

        self.student.refresh_from_db()
        self.assertEqual(self.student.student_name, "Priya S. Patil")
        self.assertEqual(self.student.section, "B")
        self.assertEqual(self.student.roll_number, "15")
        self.assertEqual(self.student.parent_phone, "9998887776")

    def test_student_id_card_view(self):
        url = reverse("students:id_card", args=[self.student.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_id_card.html")
        self.assertEqual(response.context["student"], self.student)

        content = response.content.decode("utf-8")
        self.assertIn("Priya Patil", content)
        self.assertIn("AEQ-STU-101", content)
        self.assertIn("Aequs-logo.png", content)
        self.assertIn("Student Identity Card", content)
        self.assertIn("qr", content)

    def test_student_qr_code_generates_valid_png(self):
        url = reverse("students:qr_code", args=[self.student.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        # PNG signature: 89 50 4E 47 0D 0A 1A 0A
        self.assertTrue(response.content.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_bulk_id_cards_view(self):
        url = reverse("students:bulk_id_cards")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/bulk_id_cards.html")
        self.assertIn(self.student, response.context["students"])

        content = response.content.decode("utf-8")
        self.assertIn("Bulk Student ID Cards Generator", content)
        self.assertIn("Priya Patil", content)

    def test_bulk_id_cards_filtering(self):
        # Create second student in different class
        s2 = Student.objects.create(
            admission_number="AEQ-STU-102",
            student_name="Anand Kulkarni",
            school=self.school,
            current_class="8",
            gender=Student.Gender.MALE,
            status=Student.Status.ACTIVE,
        )

        self.student.refresh_from_db()
        url = reverse("students:bulk_id_cards") + f"?class={self.student.current_class}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        students_in_context = list(response.context["students"])
        self.assertIn(self.student, students_in_context)
        self.assertNotIn(s2, students_in_context)

        # Filter for s2's class (8)
        url_s2 = reverse("students:bulk_id_cards") + "?class=8"
        response_s2 = self.client.get(url_s2)
        students_s2 = list(response_s2.context["students"])
        self.assertIn(s2, students_s2)
        self.assertNotIn(self.student, students_s2)
