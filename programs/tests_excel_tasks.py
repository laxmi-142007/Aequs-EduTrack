from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from programs.models import (
    Project,
    Program,
    EVClassSession,
    MikePropenScholarshipApplication,
)
from programs.metrics import (
    get_reach_matrix,
    get_volunteering_kpis,
    get_one_precious_notebook_kpis,
    get_budget_vs_actual,
)
from schools.models import School
from students.models import Student
from distributions.models import Distribution
from volunteers.models import Volunteer, VolunteerActivity, EmployeeTestimonial


class ExcelTasksComprehensiveTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin_test",
            email="admin_test@aequs.com",
            password="TestPassword@2026",
            role=User.Role.SUPER_ADMIN,
        )
        self.client.force_login(self.admin_user)

        # Seed test school & student
        self.school = School.objects.create(
            name="Test Model School Hattargi",
            udise_code="29010100101",
            district="Belagavi",
            taluk="Hukkeri",
        )
        self.student = Student.objects.create(
            student_name="Test Student Ananya",
            admission_number="ADM-TEST-001",
            school=self.school,
            gender="FEMALE",
        )

        # Seed projects for the 3 pillars
        self.cog_proj = Project.objects.create(
            name="Cognitive Development",
            code="PRJ-COG",
            allocated_budget=Decimal("500000.00"),
            spent_budget=Decimal("350000.00"),
        )
        self.steam_proj = Project.objects.create(
            name="STEAM Literacy Program",
            code="PRJ-STM",
            allocated_budget=Decimal("1200000.00"),
            spent_budget=Decimal("950000.00"),
        )
        self.excel_proj = Project.objects.create(
            name="Student Excel Program",
            code="PRJ-EXC",
            allocated_budget=Decimal("800000.00"),
            spent_budget=Decimal("620000.00"),
        )

        # Seed programs
        self.msl_prog = Program.objects.create(
            project=self.steam_proj,
            title="Mobile Science Lab 1- Hattargi",
            code="PRG-STM-MSL-HAT-01",
            location_name="Hattargi Cluster",
            academic_year="2026-27",
        )
        self.msl_prog.participating_schools.add(self.school)

        # Seed EV Session
        self.ev_session = EVClassSession.objects.create(
            session_title="Optics & Lenses Workshop",
            session_code="EV-TST-001",
            program=self.msl_prog,
            school=self.school,
            session_date=date(2026, 9, 15),
            duration_minutes=90,
            attendee_count=45,
            facilitator_name="Dr. Rao",
        )
        self.ev_session.students.add(self.student)

        # Seed Distribution (Notebooks)
        self.dist = Distribution.objects.create(
            benefit_type=Distribution.BenefitType.BOOK,
            recipient_type=Distribution.RecipientType.STUDENT,
            student=self.student,
            school=self.school,
            quantity=5,
            academic_year="2026-27",
            remarks="One Precious Notebook distribution",
        )

        # Seed Volunteer
        self.vol = Volunteer.objects.create(
            first_name="Ramesh",
            last_name="Kulkarni",
            email="ramesh.k@example.com",
            phone="+91 98450 11111",
            status="ACTIVE",
        )
        self.activity_completed = VolunteerActivity.objects.create(
            volunteer=self.vol,
            activity_name="STEM Lab Mentoring",
            activity_date=date(2026, 8, 10),
            status="COMPLETED",
        )
        self.activity_upcoming = VolunteerActivity.objects.create(
            volunteer=self.vol,
            activity_name="Green Campus Drive",
            activity_date=date(2026, 12, 1),
            status="ASSIGNED",
        )

    def test_reach_matrix_computation(self):
        """Verify reach matrix returns proper metrics for current and consolidated years."""
        curr = get_reach_matrix(academic_year="2026-27")
        self.assertGreaterEqual(curr["no_of_students"], 1)
        self.assertGreaterEqual(curr["no_of_schools"], 1)
        self.assertGreaterEqual(curr["no_of_learning_hrs"], 60.0)

        hist = get_reach_matrix(academic_year="all")
        self.assertGreaterEqual(hist["no_of_students"], 1)

    def test_volunteering_and_opn_kpis(self):
        """Verify volunteering and notebook distribution metrics."""
        vol_curr = get_volunteering_kpis(academic_year="2026-27")
        self.assertGreaterEqual(vol_curr["no_of_volunteers"], 1)

        opn_curr = get_one_precious_notebook_kpis(academic_year="2026-27")
        self.assertGreaterEqual(opn_curr["notebooks_donated"], 5)

        budget = get_budget_vs_actual()
        self.assertGreaterEqual(budget["allocated_total"], 2500000.0)
        self.assertGreater(budget["utilization_pct"], 0)

    def test_admin_dashboard_reach_matrix_view(self):
        """Verify admin dashboard renders Reach Matrix and filters correctly."""
        resp = self.client.get(reverse("accounts:admin_dashboard") + "?ay=2026-27")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Reach Matrix &amp; Operational Impact")
        self.assertContains(resp, "No. of Students")
        self.assertContains(resp, "Learning Hours")
        self.assertContains(resp, "AEQATRA Volunteering")
        self.assertContains(resp, "One Precious Notebook (OPN)")
        self.assertContains(resp, "Budget vs. Actual CSR Spend")

    def test_tracking_dashboard_view(self):
        """Verify the dedicated project-wise tracking dashboard."""
        resp = self.client.get(reverse("programs:tracking_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Project-Wise Tracking Dashboard")
        self.assertContains(resp, "Cognitive Development")
        self.assertContains(resp, "STEAM Literacy Program")
        self.assertContains(resp, "Student Excel Program")
        self.assertContains(resp, "Mobile Science Lab 1- Hattargi")

        # Test pillar tab filtering
        resp_steam = self.client.get(reverse("programs:tracking_dashboard") + "?tab=steam")
        self.assertEqual(resp_steam.status_code, 200)
        self.assertContains(resp_steam, "Mobile Science Lab 1- Hattargi")

    def test_aeqatra_volunteering_portal(self):
        """Verify AEQATRA Employee Volunteering Portal, activities, and testimonials."""
        resp = self.client.get(reverse("volunteers:list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "AEQATRA — Employee Volunteering Portal")
        self.assertContains(resp, "Volunteering Participation: Current Year vs. Historical Data")
        self.assertContains(resp, "List of Activities for Year")
        self.assertContains(resp, "Employee Testimonials — Video Gallery")

        # Add testimonial test
        post_resp = self.client.post(
            reverse("volunteers:testimonial_create"),
            {
                "employee_name": "Deepak Shinde",
                "employee_role": "CNC Machinist",
                "department": "Aero Structures",
                "plant_location": "Belagavi SEZ",
                "quote": "Inspiring the next generation is truly fulfilling.",
                "video_url": "https://www.youtube.com/watch?v=sample123",
                "academic_year": "2026-27",
            }
        )
        self.assertEqual(post_resp.status_code, 302)
        self.assertTrue(EmployeeTestimonial.objects.filter(employee_name="Deepak Shinde").exists())

    def test_mike_propen_scholarship_portal(self):
        """Verify Mike Propen Scholarship Application, Analysis, and Data Details."""
        # 1. Access portal analysis tab
        resp_analysis = self.client.get(reverse("programs:propen_portal") + "?tab=analysis")
        self.assertEqual(resp_analysis.status_code, 200)
        self.assertContains(resp_analysis, "Mike Propen Scholarship Scheme")
        self.assertContains(resp_analysis, "1. Analysis")
        self.assertContains(resp_analysis, "2. Data Details")
        self.assertContains(resp_analysis, "3. Application Form")

        # 2. Access data details tab
        resp_details = self.client.get(reverse("programs:propen_portal") + "?tab=details")
        self.assertEqual(resp_details.status_code, 200)

        # 3. Submit new application
        apply_resp = self.client.post(
            reverse("programs:propen_apply"),
            {
                "student_name": "Suresh Naik",
                "gender": "MALE",
                "school": str(self.school.id),
                "grade_level": "Class 10",
                "academic_percentage": "95.50",
                "annual_family_income": "60000",
                "contact_phone": "+91 98450 99999",
                "email": "suresh.n@example.com",
                "statement_of_purpose": "Aspiring engineer with distinction in science olympiad.",
                "scholarship_amount": "25000",
                "academic_year": "2026-27",
            }
        )
        self.assertEqual(apply_resp.status_code, 302)
        app = MikePropenScholarshipApplication.objects.filter(student_name="Suresh Naik").first()
        self.assertIsNotNone(app)
        self.assertTrue(app.application_number.startswith("MPS-"))
        self.assertEqual(app.status, MikePropenScholarshipApplication.Status.SUBMITTED)

        # 4. Update status workflow
        status_resp = self.client.post(
            reverse("programs:propen_update_status", kwargs={"pk": app.pk}),
            {
                "status": MikePropenScholarshipApplication.Status.AWARDED,
                "reviewer_notes": "Merit approved by committee.",
            }
        )
        self.assertEqual(status_resp.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, MikePropenScholarshipApplication.Status.AWARDED)
        self.assertEqual(app.reviewer_notes, "Merit approved by committee.")

        # 5. Export CSV
        csv_resp = self.client.get(reverse("programs:propen_export_csv"))
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp["Content-Type"], "text/csv")
        self.assertIn("Suresh Naik", csv_resp.content.decode("utf-8"))
