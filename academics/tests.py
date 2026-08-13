import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from academics.models import AcademicRecord
from students.models import Student
from schools.models import School


class AcademicSectionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(
            name="Test Model School",
            udise_code="29010200111",
            district="Bangalore",
        )
        self.student = Student.objects.create(
            student_name="Aarav Sharma",
            admission_number="ADM-2023-001",
            school=self.school,
            current_class="Class 5",
            parent_name="Mr. Sharma",
        )
        self.record = AcademicRecord.objects.create(
            student=self.student,
            academic_year="2023-2024",
            class_or_course="Class 5",
            percentage=Decimal("92.5"),
            rank=1,
            promotion_status="Promoted",
        )

    def test_portal_view(self):
        response = self.client.get(reverse("academics:portal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Academic Record Management")
        self.assertContains(response, "Aarav Sharma")

    def test_api_records_list(self):
        response = self.client.get(reverse("academics:api_records"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["records"]), 1)

    def test_api_create_record(self):
        payload = {
            "studentName": "Diya Patel",
            "academicYear": "2024-2025",
            "studentClass": "Class 6",
            "percentage": "88.0",
            "rank": "3",
            "promotionDetails": "Promoted",
            "schoolTransfer": "No",
        }
        response = self.client.post(
            reverse("academics:api_create"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["record"]["student_name"], "Diya Patel")
        self.assertTrue(AcademicRecord.objects.filter(student__student_name="Diya Patel").exists())

    def test_api_update_record(self):
        payload = {
            "percentage": "95.0",
            "rank": "1",
            "promotionDetails": "Promoted",
        }
        response = self.client.post(
            reverse("academics:api_update", args=[self.record.id]),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.record.refresh_from_db()
        self.assertEqual(self.record.percentage, Decimal("95.0"))

    def test_api_delete_record(self):
        response = self.client.post(reverse("academics:api_delete", args=[self.record.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AcademicRecord.objects.filter(id=self.record.id).exists())

    def test_api_get_students(self):
        response = self.client.get(reverse("academics:api_students"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["students"]), 1)
