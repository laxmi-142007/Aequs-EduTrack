import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from schools.models import School
from students.models import Student
from eligibility.models import EligibilityRecord, BenefitType
from internships.models import (
    InternshipProgram,
    InternshipPlacement,
    InternshipMilestone,
    Department,
)
from internships.services import (
    get_internship_kpis,
    generate_certificate_number,
    get_eligible_students_for_internship,
)


class InternshipModelTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Government Science PU College",
            udise_code="29010100199",
            district="Belagavi",
            taluk="Belagavi City",
            status=School.Status.ACTIVE,
        )
        self.student = Student.objects.create(
            admission_number="ADM-INT-001",
            student_name="Kavya Patil",
            school=self.school,
            current_class="B.E. Mechanical",
            gender=Student.Gender.FEMALE,
            status=Student.Status.ACTIVE,
        )
        self.program = InternshipProgram.objects.create(
            title="Aequs Aerospace Precision Engineering",
            program_code="AEQ-TEST-001",
            company_name="Aequs Aerospace SEZ",
            department=Department.PRECISION_MANUFACTURING,
            stipend_amount=Decimal("10000.00"),
            total_slots=10,
            status=InternshipProgram.Status.OPEN,
        )

    def test_program_capacity_properties(self):
        self.assertEqual(self.program.enrolled_count, 0)
        self.assertEqual(self.program.available_slots, 10)

        placement = InternshipPlacement.objects.create(
            student=self.student,
            program=self.program,
            school=self.school,
            department=self.program.department,
            status=InternshipPlacement.Status.SELECTED,
        )

        self.assertEqual(self.program.enrolled_count, 1)
        self.assertEqual(self.program.available_slots, 9)

    def test_placement_certificate_generation(self):
        placement = InternshipPlacement.objects.create(
            student=self.student,
            program=self.program,
            school=self.school,
            department=self.program.department,
            status=InternshipPlacement.Status.COMPLETED,
            certificate_issued=True,
        )
        cert_no = generate_certificate_number(placement)
        self.assertTrue(cert_no.startswith("AEQ-CERT-"))
        self.assertIn(str(placement.id), cert_no)

    def test_services_kpis(self):
        InternshipPlacement.objects.create(
            student=self.student,
            program=self.program,
            school=self.school,
            department=self.program.department,
            status=InternshipPlacement.Status.IN_PROGRESS,
            stipend_amount=Decimal("10000.00"),
        )
        kpis = get_internship_kpis()
        self.assertEqual(kpis["total_interns"], 1)
        self.assertEqual(kpis["active_interns"], 1)
        self.assertEqual(kpis["total_programs"], 1)
        self.assertEqual(kpis["total_stipend"], 10000.00)


class InternshipAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Government Engineering College",
            udise_code="29010100200",
            district="Belagavi",
            status=School.Status.ACTIVE,
        )
        self.student = Student.objects.create(
            admission_number="ADM-INT-002",
            student_name="Basavaraj Bellad",
            school=self.school,
            current_class="Degree Mechanical",
            gender=Student.Gender.MALE,
            status=Student.Status.ACTIVE,
        )
        self.program = InternshipProgram.objects.create(
            title="Quality Assurance Track",
            program_code="AEQ-TEST-QA",
            company_name="Aequs Aerospace",
            department=Department.QUALITY_ASSURANCE,
            stipend_amount=Decimal("9000.00"),
            total_slots=5,
            status=InternshipProgram.Status.OPEN,
        )

    def test_portal_view(self):
        response = self.client.get(reverse("internships:portal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Internship Management Portal")

    def test_api_list_internships(self):
        response = self.client.get(reverse("internships:api_internships"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_api_create_internship(self):
        payload = {
            "student_id": self.student.id,
            "program_id": self.program.id,
            "department": Department.QUALITY_ASSURANCE,
            "company_name": "Aequs Aerospace",
            "project_title": "CMM Calibration Study",
            "stipend_amount": 9000.00,
            "academic_year": "2026-27",
            "status": InternshipPlacement.Status.SELECTED,
            "mentor_name": "Deepa Patil",
        }
        response = self.client.post(
            reverse("internships:api_create_internship"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["placement"]["student_name"], "Basavaraj Bellad")

    def test_api_update_status_and_certify(self):
        placement = InternshipPlacement.objects.create(
            student=self.student,
            program=self.program,
            school=self.school,
            department=self.program.department,
            status=InternshipPlacement.Status.IN_PROGRESS,
        )
        url = reverse("internships:api_update_status", args=[placement.id])
        payload = {
            "status": InternshipPlacement.Status.COMPLETED,
            "performance_grade": InternshipPlacement.PerformanceGrade.OUTSTANDING,
            "evaluation_feedback": "Excellent work and dedication throughout.",
            "issue_certificate": True,
        }
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["placement"]["certificate_issued"])
        self.assertTrue(data["placement"]["certificate_number"].startswith("AEQ-CERT-"))

    def test_api_quick_assign_candidate(self):
        payload = {
            "student_id": self.student.id,
            "program_id": self.program.id,
        }
        response = self.client.post(
            reverse("internships:api_quick_assign"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(InternshipPlacement.objects.filter(student=self.student).count(), 1)

    def test_api_export_csv(self):
        response = self.client.get(reverse("internships:export_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
