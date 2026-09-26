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
        self.client.force_login(self.user)
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
        response = self.client.get(reverse("schools:portal"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Government Schools")
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
        from distributions.models import Distribution
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

    def test_bulk_upload_schools_with_taluk(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_content = (
            "name,udise_code,taluk\n"
            "Taluk Test School,29999900001,Hukkeri\n"
        ).encode("utf-8")
        uploaded_file = SimpleUploadedFile("schools.csv", csv_content, content_type="text/csv")
        response = self.client.post(
            reverse("schools:bulk_upload"),
            {"school_file": uploaded_file},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        school = School.objects.filter(udise_code="29999900001").first()
        self.assertIsNotNone(school)
        self.assertEqual(school.taluk, "Hukkeri")
        self.assertEqual(school.district, "Hukkeri")

    def test_bulk_upload_schools_missing_taluk_fails(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_content = (
            "name,udise_code,district\n"
            "No Taluk School,29999900002,Belagavi\n"
        ).encode("utf-8")
        uploaded_file = SimpleUploadedFile("schools.csv", csv_content, content_type="text/csv")
        response = self.client.post(
            reverse("schools:bulk_upload"),
            {"school_file": uploaded_file},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(School.objects.filter(udise_code="29999900002").exists())

    def test_bulk_upload_user_roster_format(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        roster_data = (
            "SL NO\tSCHOOL NAME\tTaluk\tUDISE CODE\tHM Name\tMOBILE\tScience Teacher Name\tMOBILE\tDivision\tCLASS 4th\t\t\tCLASS 5th \t\t\tCLASS 6th (DLC)\t\t\tCLASS 7th\t\t\tCLASS 8th \t\t\tCLASS 9th \t\t\tCLASS 10th \t\t\tGRAND Total\t\t\tRemarks\n"
            "\t\t\t\t\t\t\t\t\tBOYS\tGIRLS\tTOTAL\tBOYS\tGIRLS\tTOTAL\tBOYS\tGIRLS\tTOTAL\tBOYS\tGIRLS\tTOTAL\tBOYS\tGIRLS\tTOTAL\tBOYS\tGIRLS\tTOTAL\tBOYS\tGIRLS\tTOTAL\tBOYS\tGIRLS\tTOTAL\t\n"
            "1\tGMPS Amaragol\tHubli Rural\t29090210101\tSri.B V Bommanavadi\t6360625288\tSmt.V M Patange\t9482377611\tA\t10\t20\t30\t20\t11\t31\t12\t11\t23\t10\t16\t26\t\t\t0\t\t\t0\t\t\t0\t52\t58\t110\t\n"
            "\t\t\t\t\t\t\t\tB\t9\t19\t28\t20\t10\t30\t13\t12\t25\t10\t17\t27\t\t\t0\t\t\t0\t\t\t0\t52\t58\t110\t\n"
            "2\tGMPS Tarihal\tHubli Rural\t29090204801\tSri.Basavaraj Bandiwad\t8867064585\tSmt.M S Annigeri\t8050978579\tA\t15\t15\t30\t17\t17\t34\t13\t12\t25\t15\t15\t30\t\t\t0\t\t\t0\t\t\t0\t60\t59\t119\t\n"
            "\t\t\t\t\t\t\t\tB\t17\t15\t32\t18\t19\t37\t10\t13\t23\t15\t18\t33\t\t\t0\t\t\t0\t\t\t0\t60\t65\t125\t\n"
            "8\tGHPS Itigatti\tDharwad City\t29090702110\tSri.M L Pujar\t9902153087\tSmt .J Kanchanor\t9620680336\t\t15\t10\t25\t21\t29\t50\t23\t22\t45\t19\t28\t47\t20\t29\t49\t\t\t0\t\t\t0\t98\t118\t216\t\n"
            "9\tGHS Itigatti\tDharwad City\t29090702110\tSri.Rajkumar Chavhan\t9901812166\tSmt..A D Ambannavar\t9480555342\t\t\t\t0\t\t\t0\t\t\t0\t\t\t0\t14\t23\t37\t14\t26\t40\t\t\t0\t28\t49\t77\t\n"
            "\t\t\t\t\t\t\t\t\t333\t326\t659\t387\t414\t801\t330\t408\t738\t345\t421\t766\t277\t296\t573\t72\t113\t185\t0\t0\t0\t1744\t1978\t3,722\t\n"
        ).encode("utf-8")
        uploaded_file = SimpleUploadedFile("roster.csv", roster_data, content_type="text/csv")
        response = self.client.post(
            reverse("schools:bulk_upload"),
            {"school_file": uploaded_file},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify GMPS Amaragol
        amaragol = School.objects.filter(name="GMPS Amaragol").first()
        self.assertIsNotNone(amaragol)
        self.assertEqual(amaragol.taluk, "Hubli Rural")
        self.assertEqual(amaragol.headmaster_name, "Sri.B V Bommanavadi")
        self.assertEqual(amaragol.headmaster_phone, "6360625288")
        # 110 (div A) + 110 (div B) = 220
        self.assertEqual(amaragol.student_strength, 220)

        # Check grade strengths for Amaragol (Class 4th: 19 boys, 39 girls = 58 total)
        c4 = amaragol.grade_strengths.filter(grade_level__icontains="CLASS 4").first()
        self.assertIsNotNone(c4)
        self.assertEqual(c4.total_students, 58)

        # Verify Science Teacher resource
        teacher_res = SchoolResource.objects.filter(school=amaragol, resource_name__icontains="Patange").first()
        self.assertIsNotNone(teacher_res)

        # Verify duplicate UDISE disambiguation for GHS and GHPS Itigatti
        ghps = School.objects.filter(name="GHPS Itigatti").first()
        ghs = School.objects.filter(name="GHS Itigatti").first()
        self.assertIsNotNone(ghps)
        self.assertIsNotNone(ghs)
        self.assertNotEqual(ghps.udise_code, ghs.udise_code)

    def test_bulk_upload_with_leading_title_rows(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_content = (
            "AEQUS FOUNDATION EDUCATION PROGRAM\n"
            "Dharwad Cluster School Details 2024-25\n"
            "SL NO,SCHOOL NAME,Taluk,UDISE CODE,HM Name\n"
            "1,Title Test School,Dharwad Rural,29999900088,Sri Headmaster\n"
        ).encode("utf-8")
        uploaded_file = SimpleUploadedFile("schools_with_title.csv", csv_content, content_type="text/csv")
        response = self.client.post(
            reverse("schools:bulk_upload"),
            {"school_file": uploaded_file},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        school = School.objects.filter(udise_code="29999900088").first()
        self.assertIsNotNone(school)
        self.assertEqual(school.name, "Title Test School")
        self.assertEqual(school.taluk, "Dharwad Rural")

