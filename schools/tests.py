import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import School, SchoolMilestone, SchoolResource, GradeStrength

User = get_user_model()


class SchoolPortalAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="admin",
            password="admin123",
            role=User.Role.ADMIN,
        )
        self.school = School.objects.create(
            name="Test Govt High School",
            udise_code="29010200999",
            village="Sample Village",
            district="Bangalore",
            phone="+91 99999 88888",
            email="test@school.edu",
            website="https://testschool.edu",
            headmaster_name="Mr. Principal",
            headmaster_qualification="M.Ed.",
            headmaster_experience=10,
            affiliation="State",
        )

    def test_portal_view(self):
        response = self.client.get(reverse("schools:portal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Government School Management System")
        self.assertContains(response, "Test Govt High School")

    def test_api_schools_list(self):
        response = self.client.get(reverse("schools:api_schools_list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["schools"]), 1)

    def test_api_school_detail(self):
        response = self.client.get(reverse("schools:api_school_detail", args=[self.school.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["school"]["name"], "Test Govt High School")
        self.assertIn("strengths", data)
        self.assertIn("milestones", data)
        self.assertIn("resources", data)

    def test_api_add_school(self):
        payload = {
            "schoolName": "New Rural Govt School",
            "village": "Rural Village",
            "state": "Mysore",
            "admissionDate": "2025-06-01",
            "affiliation": "CBSE",
        }
        response = self.client.post(
            reverse("schools:api_add_school"),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["school"]["name"], "New Rural Govt School")
        self.assertTrue(School.objects.filter(name="New Rural Govt School").exists())

    def test_api_edit_school(self):
        payload = {
            "editSchoolName": "Updated Govt High School",
            "editPrincipal": "Dr. New Principal",
            "editAffiliation": "CBSE",
        }
        response = self.client.post(
            reverse("schools:api_edit_school", args=[self.school.id]),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.school.refresh_from_db()
        self.assertEqual(self.school.name, "Updated Govt High School")
        self.assertEqual(self.school.headmaster_name, "Dr. New Principal")
        self.assertEqual(self.school.affiliation, "CBSE")

    def test_api_update_contact(self):
        payload = {
            "phone": "+91 88888 77777",
            "email": "updated@school.edu",
            "website": "https://updatedschool.edu",
        }
        response = self.client.post(
            reverse("schools:api_update_contact", args=[self.school.id]),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.school.refresh_from_db()
        self.assertEqual(self.school.phone, "+91 88888 77777")
        self.assertEqual(self.school.email, "updated@school.edu")

    def test_api_update_headmaster(self):
        response = self.client.post(
            reverse("schools:api_update_headmaster", args=[self.school.id]),
            data={
                "headmasterName": "Prof. John Doe",
                "headmasterQualification": "Ph.D.",
                "headmasterExperience": 22,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.school.refresh_from_db()
        self.assertEqual(self.school.headmaster_name, "Prof. John Doe")
        self.assertEqual(self.school.headmaster_experience, 22)

    def test_api_milestone_crud(self):
        # Add milestone
        payload = {
            "title": "New Computer Lab",
            "year_or_date": "2024",
            "details": "Installed 30 PCs",
            "impact": "Boosted digital literacy",
        }
        response = self.client.post(
            reverse("schools:api_add_milestone", args=[self.school.id]),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        milestone_id = response.json()["milestone"]["id"]
        self.assertTrue(SchoolMilestone.objects.filter(id=milestone_id).exists())

        # Delete milestone
        del_response = self.client.post(
            reverse("schools:api_delete_milestone", args=[milestone_id])
        )
        self.assertEqual(del_response.status_code, 200)
        self.assertFalse(SchoolMilestone.objects.filter(id=milestone_id).exists())

    def test_api_resource_crud(self):
        from distributions.models import Distribution
        from inventory.models import InventoryItem, InventoryCategory

        inv_item = InventoryItem.objects.create(
            item_name="Library Books Set",
            sku="BK-LIB-SET-01",
            category=InventoryCategory.BOOKS,
            unit="Sets",
            current_stock=1000,
            status="ACTIVE",
        )

        from distributions.models import Distribution
        from inventory.models import InventoryItem, InventoryCategory

        inv_item = InventoryItem.objects.create(
            item_name="Library Books Set",
            sku="BK-LIB-SET-01",
            category=InventoryCategory.BOOKS,
            unit="Sets",
            current_stock=1000,
            status="ACTIVE",
        )

        # Add resource / distribution / distribution
        payload = {
            "item_id": inv_item.id,
            "resource_name": inv_item.item_name,
            "status": "Delivered",
            "quantity": 500,
            "last_updated_note": "May 2024",
            "details": "Science and literature collection",
        }
        response = self.client.post(
            reverse("schools:api_add_resource", args=[self.school.id]),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        res_id = response.json()["resource"]["id"]
        self.assertTrue(SchoolResource.objects.filter(id=res_id).exists())
        self.assertTrue(Distribution.objects.filter(school=self.school, quantity=500).exists())

        inv_item.refresh_from_db()
        self.assertEqual(inv_item.current_stock, 500)

        # Delete resource / distribution
        del_response = self.client.post(
            reverse("schools:api_delete_resource", args=[res_id])
        )
        self.assertEqual(del_response.status_code, 200)
        self.assertFalse(SchoolResource.objects.filter(id=res_id).exists())
        self.assertFalse(Distribution.objects.filter(school=self.school, quantity=500).exists())

    def test_api_clear_all_schools(self):
        response = self.client.post(reverse("schools:api_clear_all_schools"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(School.objects.count(), 0)
        self.assertFalse(Distribution.objects.filter(school=self.school, quantity=500).exists())

    def test_export_student_strength_csv(self):
        response = self.client.get(reverse("schools:export_strength_csv", args=[self.school.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("Grade Level", content)
        self.assertIn("Male Students", content)

    def test_clear_all_students_endpoint(self):
        from students.models import Student
        Student.objects.create(
            admission_number="ST-9999",
            student_name="Test Student Clear",
            gender="MALE",
            school=self.school,
            current_class="10"
        )
        self.assertTrue(Student.objects.filter(admission_number="ST-9999").exists())
        response = self.client.post(reverse("students:clear_all"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Student.objects.filter(admission_number="ST-9999").exists())

    def test_api_auth_login(self):
        response = self.client.post(
            reverse("schools:api_login"),
            data=json.dumps({"username": "admin", "password": "admin123"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
