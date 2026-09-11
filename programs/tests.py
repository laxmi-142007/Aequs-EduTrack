from datetime import date, time
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError

from accounts.models import User
from schools.models import School
from students.models import Student
from academics.models import AcademicRecord, SubjectScore
from events.models import Event
from programs.models import NGO, Project, Program, EVClassSession, Scholarship, CSRGrant, Location, MentorshipSession
from internships.models import InternshipProgram, InternshipPlacement, Department
from programs.views import ensure_default_ngos


class ProgramsAndFoundationModulesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username="admin_test",
            email="admin@aequs.com",
            password="adminpassword123",
        )
        self.client.force_login(self.user)

        self.school = School.objects.create(
            name="GHPS Kakati Belagavi",
            udise_code="UDISE-KAK-001",
            village="Kakati",
            taluk="Belagavi",
            district="Belagavi",
        )

        self.student = Student.objects.create(
            student_name="Rohit Patil",
            admission_number="ADM-2026-999",
            school=self.school,
            current_class="8",
            gender=Student.Gender.MALE,
            parent_phone="9876543210",
            parental_consent_obtained=True,
            consent_date=date(2026, 1, 15),
            consent_ref="CONSENT-AF-001",
        )

    # ------------------------------------------------------------------------
    # Module 5: NGO Management
    # ------------------------------------------------------------------------
    def test_ngo_auto_seeding_and_list(self):
        ensure_default_ngos()
        self.assertTrue(NGO.objects.filter(code="PRATHAM").exists())
        self.assertTrue(NGO.objects.filter(code="AGASTYA").exists())
        self.assertTrue(NGO.objects.filter(code="YFS").exists())

        response = self.client.get(reverse("programs:ngo_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pratham")
        self.assertContains(response, "Agastya International Foundation")
        self.assertContains(response, "Youth for Seva")

    # ------------------------------------------------------------------------
    # Module 7: Project Tab & Tracking
    # ------------------------------------------------------------------------
    def test_project_lifecycle_and_budget(self):
        ngo = NGO.objects.create(name="Pratham Belagavi", code="PRATHAM-BLG")
        project = Project.objects.create(
            name="Foundational Literacy Drive",
            code="PRJ-FLN-01",
            ngo=ngo,
            start_date=date(2026, 1, 1),
            allocated_budget=Decimal("500000.00"),
            spent_budget=Decimal("150000.00"),
            status=Project.Status.ACTIVE,
        )
        project.target_schools.add(self.school)

        response = self.client.get(reverse("programs:project_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PRJ-FLN-01")
        self.assertContains(response, "Foundational Literacy Drive")

        # Detail view
        detail_resp = self.client.get(reverse("programs:project_detail", kwargs={"pk": project.pk}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "500000")

        # Toggle archive
        arch_resp = self.client.get(reverse("programs:project_toggle_archive", kwargs={"pk": project.pk}))
        self.assertEqual(arch_resp.status_code, 302)
        project.refresh_from_db()
        self.assertTrue(project.is_archived)

    # ------------------------------------------------------------------------
    # Module 11 & 16: Programs with Mandatory Location
    # ------------------------------------------------------------------------
    def test_program_mandatory_location(self):
        program = Program.objects.create(
            title="Mobile Science Discovery Lab",
            code="PRG-MSL-01",
            category=Program.Category.STEM,
            location_name="Kakati Govt Campus",
            village_or_town="Kakati",
            taluk="Belagavi",
            district="Belagavi",
            state="Karnataka",
        )
        program.participating_schools.add(self.school)

        response = self.client.get(reverse("programs:program_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kakati Govt Campus")
        self.assertContains(response, "PRG-MSL-01")

        detail_resp = self.client.get(reverse("programs:program_detail", kwargs={"pk": program.pk}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Belagavi")

    # ------------------------------------------------------------------------
    # Module 4: Detailed EV Class Tracking
    # ------------------------------------------------------------------------
    def test_ev_class_session_tracking(self):
        session = EVClassSession.objects.create(
            session_title="Solar Energy Hands-on Workshop",
            session_code="EV-2026-001",
            school=self.school,
            grade_level="8",
            topic="Renewable Energy & Photovoltaics",
            session_date=date(2026, 2, 10),
            start_time=time(10, 0),
            end_time=time(12, 0),
            duration_minutes=120,
            facilitator_name="Dr. Anand Deshpande",
            attendee_count=45,
            pre_assessment_avg=Decimal("42.50"),
            post_assessment_avg=Decimal("84.00"),
            status=EVClassSession.Status.COMPLETED,
        )

        response = self.client.get(reverse("programs:ev_class_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EV-2026-001")
        self.assertContains(response, "Solar Energy Hands-on Workshop")

        detail_resp = self.client.get(reverse("programs:ev_class_detail", kwargs={"pk": session.pk}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Dr. Anand Deshpande")
        self.assertContains(detail_resp, "84")

    # ------------------------------------------------------------------------
    # Module 8 & 9: Scholarships (Foundation, Govt, Employee Special)
    # ------------------------------------------------------------------------
    def test_scholarships_and_special_tabs(self):
        # 1. Government Scholarship (SSP)
        govt_sch = Scholarship.objects.create(
            student=self.student,
            category=Scholarship.Category.GOVERNMENT,
            scheme_name="Karnataka State Scholarship Portal (SSP)",
            application_number="SSP-2026-00119",
            academic_year="2025-26",
            sanctioned_amount=Decimal("4500.00"),
            disbursed_amount=Decimal("4500.00"),
            disbursement_date=date(2026, 2, 15),
            status=Scholarship.Status.DISBURSED,
            aadhaar_verified=True,
            income_cert_verified=True,
            bank_account_verified=True,
        )

        # 2. Employee Special Scheme
        emp_sch = Scholarship.objects.create(
            student=self.student,
            category=Scholarship.Category.EMPLOYEE_SPECIAL,
            scheme_name="Aequs Employee Child Education Grant",
            application_number="EMP-EDU-909",
            academic_year="2025-26",
            sanctioned_amount=Decimal("12000.00"),
            employee_code="AEQ-BLG-445",
            employee_name="Suresh Patil",
            employee_department="Aerospace Machining",
            plant_location="Belagavi SEZ",
            status=Scholarship.Status.SANCTIONED,
        )

        # List view with all
        response = self.client.get(reverse("programs:scholarship_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SSP-2026-00119")
        self.assertContains(response, "EMP-EDU-909")

        # Tab views
        govt_tab = self.client.get(reverse("programs:scholarship_list") + "?tab=government")
        self.assertContains(govt_tab, "SSP-2026-00119")

        emp_tab = self.client.get(reverse("programs:scholarship_list") + "?tab=employee_special")
        self.assertContains(emp_tab, "AEQ-BLG-445")
        self.assertContains(emp_tab, "Belagavi SEZ")

        # Update status action
        status_resp = self.client.post(
            reverse("programs:scholarship_update_status", kwargs={"pk": emp_sch.pk}),
            {"status": "DISBURSED"},
        )
        self.assertEqual(status_resp.status_code, 302)
        emp_sch.refresh_from_db()
        self.assertEqual(emp_sch.status, Scholarship.Status.DISBURSED)

    # ------------------------------------------------------------------------
    # Module 6: Monthly Tracking
    # ------------------------------------------------------------------------
    def test_monthly_tracking_aggregation(self):
        today = date.today()
        EVClassSession.objects.create(
            session_title="Robotics Intro",
            session_code="EV-ROB-01",
            school=self.school,
            grade_level="7",
            topic="Robotics",
            session_date=today,
            start_time=time(9, 30),
            attendee_count=30,
        )

        response = self.client.get(
            reverse("programs:monthly_tracking") + f"?month={today.month}&year={today.year}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Robotics Intro")
        self.assertContains(response, "Monthly Foundation Tracking")

    # ------------------------------------------------------------------------
    # Module 17: Archive Portal
    # ------------------------------------------------------------------------
    def test_archive_portal_and_restoration(self):
        project = Project.objects.create(
            name="Archived Science Fair",
            code="PRJ-OLD-01",
            start_date=date(2025, 1, 1),
            is_archived=True,
        )

        response = self.client.get(reverse("programs:archive_portal") + "?tab=projects")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PRJ-OLD-01")

        # Restore
        restore_resp = self.client.get(
            reverse("programs:archive_restore", kwargs={"model_type": "project", "pk": project.pk})
        )
        self.assertEqual(restore_resp.status_code, 302)
        project.refresh_from_db()
        self.assertFalse(project.is_archived)

    # ------------------------------------------------------------------------
    # Module 3: Separate Subject Tracking
    # ------------------------------------------------------------------------
    def test_subject_score_grade_and_percentage(self):
        academic_rec = AcademicRecord.objects.create(
            student=self.student,
            academic_year="2025-26",
            class_or_course="8",
            marks_obtained=Decimal("450.00"),
            total_marks=Decimal("500.00"),
        )
        sub = SubjectScore.objects.create(
            academic_record=academic_rec,
            subject_name="Mathematics",
            exam_type=SubjectScore.ExamType.ANNUAL,
            marks_obtained=Decimal("94.00"),
            max_marks=Decimal("100.00"),
        )
        self.assertEqual(sub.percentage, Decimal("94.00"))
        self.assertEqual(sub.grade, "A+")

        sub2 = SubjectScore.objects.create(
            academic_record=academic_rec,
            subject_name="Science",
            exam_type=SubjectScore.ExamType.ANNUAL,
            marks_obtained=Decimal("76.00"),
            max_marks=Decimal("100.00"),
        )
        self.assertEqual(sub2.percentage, Decimal("76.00"))
        self.assertEqual(sub2.grade, "B+")

        # Check detail page rendering
        detail_resp = self.client.get(reverse("students:detail", kwargs={"pk": self.student.pk}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Mathematics")
        self.assertContains(detail_resp, "94.00/100.00")

    # ------------------------------------------------------------------------
    # Module 10: Event Reminder Feature
    # ------------------------------------------------------------------------
    def test_event_reminder_dispatch(self):
        event = Event.objects.create(
            title="Annual STEM Discovery Fair",
            event_date=date(2026, 3, 20),
            location="Aequs SEZ Belagavi",
        )
        self.assertFalse(event.reminder_sent)

        response = self.client.post(reverse("events:send_reminder", kwargs={"pk": event.pk}))
        self.assertEqual(response.status_code, 302)
        event.refresh_from_db()
        self.assertTrue(event.reminder_sent)
        self.assertIsNotNone(event.reminder_scheduled_date)

    # ------------------------------------------------------------------------
    # Module 18: Data Protection Act (DPDP) Compliance
    # ------------------------------------------------------------------------
    def test_dpdp_parental_consent_and_masking(self):
        self.assertTrue(self.student.parental_consent_obtained)
        self.assertEqual(self.student.masked_phone, "XXXXXX3210")

        # Non-admin user sees masked phone
        volunteer_user = User.objects.create_user(
            username="volunteer_user",
            email="vol@aequs.com",
            password="volpassword123",
            role=User.Role.VOLUNTEER,
        )
        self.client.force_login(volunteer_user)
        response = self.client.get(reverse("students:detail", kwargs={"pk": self.student.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "XXXXXX3210")
        self.assertContains(response, "DPDP Parental Consent")

    # ------------------------------------------------------------------------
    # Sidebar Navigation: Tracking, Scholarship, Extra Dropdowns & Shortcuts
    # ------------------------------------------------------------------------
    def test_sidebar_dropdown_groups_and_shortcuts(self):
        response = self.client.get(reverse("programs:project_list"))
        self.assertEqual(response.status_code, 200)

        # 1. Tracking Dropdown with + shortcuts
        self.assertContains(response, "dropdownTracking")
        self.assertContains(response, reverse("programs:project_create"))
        self.assertContains(response, reverse("programs:program_create"))
        self.assertContains(response, reverse("programs:monthly_tracking"))

        # 2. Scholarship Dropdown with Eligibility, Internships, Mentorship
        self.assertContains(response, "dropdownScholarship")
        self.assertContains(response, reverse("programs:scholarship_list"))
        self.assertContains(response, reverse("eligibility:portal"))
        self.assertContains(response, reverse("internships:portal"))

        # 3. Ekatra Dropdown with Volunteers, Events, Reports, Archive
        self.assertContains(response, "dropdownEkatra")
        self.assertContains(response, "Ekatra")
        self.assertContains(response, reverse("volunteers:list"))
        self.assertContains(response, reverse("events:list"))
        self.assertContains(response, reverse("reports:list"))
        self.assertContains(response, reverse("programs:archive_portal"))

    # ------------------------------------------------------------------------
    # Feature 1: Project Code Auto Generation
    # ------------------------------------------------------------------------
    def test_project_code_auto_generation(self):
        # 1. Blank code auto generates PRJ-YYYY-###
        current_year = date.today().year
        p1 = Project.objects.create(name="Auto Code Test Project 1", code="")
        self.assertTrue(p1.code.startswith(f"PRJ-{current_year}-"))

        # 2. Sequential increment
        p2 = Project.objects.create(name="Auto Code Test Project 2", code="")
        self.assertTrue(p2.code.startswith(f"PRJ-{current_year}-"))
        self.assertNotEqual(p1.code, p2.code)

        # 3. Explicit code is preserved
        p3 = Project.objects.create(name="Manual Code Project", code="CUSTOM-PRJ-999")
        self.assertEqual(p3.code, "CUSTOM-PRJ-999")

    # ------------------------------------------------------------------------
    # Feature 2: Multi-select Location on Project and Program
    # ------------------------------------------------------------------------
    def test_multi_select_locations_project_and_program(self):
        loc1 = Location.objects.create(name="Belagavi Main Campus", code="LOC-T-01", district="Belagavi")
        loc2 = Location.objects.create(name="Koppal Outreach Hub", code="LOC-T-02", district="Koppal")

        project = Project.objects.create(name="Multi Loc Project", code="PRJ-MLOC-01")
        project.locations.add(loc1, loc2)
        self.assertEqual(project.locations.count(), 2)

        program = Program.objects.create(
            title="Multi Loc STEM Lab",
            code="PRG-MLOC-01",
            category=Program.Category.STEM,
            location_name="Belagavi Main Campus",
            district="Belagavi",
        )
        program.locations.add(loc1, loc2)
        self.assertEqual(program.locations.count(), 2)

        # Verify on project detail & program detail pages
        p_resp = self.client.get(reverse("programs:project_detail", kwargs={"pk": project.pk}))
        self.assertEqual(p_resp.status_code, 200)
        self.assertContains(p_resp, "Belagavi Main Campus")
        self.assertContains(p_resp, "Koppal Outreach Hub")

        prg_resp = self.client.get(reverse("programs:program_detail", kwargs={"pk": program.pk}))
        self.assertEqual(prg_resp.status_code, 200)
        self.assertContains(prg_resp, "Belagavi Main Campus")
        self.assertContains(prg_resp, "Koppal Outreach Hub")

    # ------------------------------------------------------------------------
    # Feature 3: Location Master CRUD
    # ------------------------------------------------------------------------
    def test_location_master_crud(self):
        # 1. Create
        create_resp = self.client.post(
            reverse("programs:location_create"),
            {
                "name": "Hubballi Skill Centre",
                "code": "LOC-HUB-01",
                "district": "Dharwad",
                "taluk": "Hubballi",
                "village_or_town": "Hubballi",
                "state": "Karnataka",
                "pincode": "580020",
                "address": "Gokul Road Industrial Estate",
                "is_active": "on",
            },
        )
        self.assertEqual(create_resp.status_code, 302)
        loc = Location.objects.get(code="LOC-HUB-01")
        self.assertEqual(loc.name, "Hubballi Skill Centre")

        # 2. List
        list_resp = self.client.get(reverse("programs:location_list"))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, "Hubballi Skill Centre")
        self.assertContains(list_resp, "LOC-HUB-01")

        # 3. Edit
        edit_resp = self.client.post(
            reverse("programs:location_edit", kwargs={"pk": loc.pk}),
            {
                "name": "Hubballi Advanced Innovation Lab",
                "code": "LOC-HUB-01",
                "district": "Dharwad",
                "taluk": "Hubballi",
                "village_or_town": "Hubballi",
                "state": "Karnataka",
                "pincode": "580020",
                "address": "Gokul Road Industrial Estate",
                "is_active": "on",
            },
        )
        self.assertEqual(edit_resp.status_code, 302)
        loc.refresh_from_db()
        self.assertEqual(loc.name, "Hubballi Advanced Innovation Lab")

        # 4. Delete
        del_resp = self.client.post(reverse("programs:location_delete", kwargs={"pk": loc.pk}))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(Location.objects.filter(code="LOC-HUB-01").exists())

    # ------------------------------------------------------------------------
    # Feature 4: Scholarship, Mentorship & Internship Connect to Project/Program
    # ------------------------------------------------------------------------
    def test_scholarship_mentorship_internship_links(self):
        project = Project.objects.create(name="Aequs Aerospace Scholars", code="PRJ-AERO-01")
        program = Program.objects.create(
            title="Aero Engineering Fellowship",
            code="PRG-AERO-01",
            category=Program.Category.SCHOLARSHIP,
            location_name="SEZ Belagavi",
            district="Belagavi",
            project=project,
        )

        # 1. Scholarship connected to project and program
        scholarship = Scholarship.objects.create(
            student=self.student,
            category=Scholarship.Category.FOUNDATION,
            scheme_name="Aequs Excellence Fellowship",
            application_number="APP-AERO-001",
            sanctioned_amount=Decimal("25000.00"),
            disbursed_amount=Decimal("25000.00"),
            status=Scholarship.Status.DISBURSED,
            project=project,
            program=program,
        )

        # 2. Mentorship connected to project and program
        mentorship = MentorshipSession.objects.create(
            session_title="Aero Dynamics & Career Pathways",
            session_code="MNT-2026-001",
            project=project,
            program=program,
            student=self.student,
            mentor_name="Rajesh Patil",
            mentor_email="rajesh.p@aequs.com",
            mentor_designation="Senior Manufacturing Lead",
            session_date=date(2026, 3, 15),
            duration_minutes=60,
            status=MentorshipSession.Status.COMPLETED,
        )

        # 3. Internship connected to project and program
        intern_prg = InternshipProgram.objects.create(
            title="Aequs Precision Engineering Internship",
            program_code="INT-AERO-01",
            company_name="Aequs Aerospace",
            project=project,
            linked_program=program,
        )
        intern_placement = InternshipPlacement.objects.create(
            student=self.student,
            school=self.school,
            program=intern_prg,
            project=project,
            linked_program=program,
            department=Department.AEROSPACE_ENG,
            project_title="Precision Machining Simulation",
            start_date=date(2026, 4, 1),
            stipend_amount=Decimal("12000.00"),
            status=InternshipPlacement.Status.SELECTED,
        )

        # Verify on Project Detail view
        prj_resp = self.client.get(reverse("programs:project_detail", kwargs={"pk": project.pk}))
        self.assertEqual(prj_resp.status_code, 200)
        self.assertContains(prj_resp, "Aequs Excellence Fellowship")
        self.assertContains(prj_resp, "MNT-2026-001")
        self.assertContains(prj_resp, "Precision Machining Simulation")

        # Verify on Program Detail view
        prog_resp = self.client.get(reverse("programs:program_detail", kwargs={"pk": program.pk}))
        self.assertEqual(prog_resp.status_code, 200)
        self.assertContains(prog_resp, "Aequs Excellence Fellowship")
        self.assertContains(prog_resp, "MNT-2026-001")
        self.assertContains(prog_resp, "Precision Machining Simulation")

    # ------------------------------------------------------------------------
    # Feature 5: Event Reminder System
    # ------------------------------------------------------------------------
    def test_event_reminder_workflow(self):
        from datetime import timedelta
        today = date.today()
        event_date = today + timedelta(days=2)
        event = Event.objects.create(
            title="Science Fair Belagavi",
            event_date=event_date,
            reminder_scheduled_date=today,
            status=Event.Status.PLANNED,
            reminder_sent=False,
        )

        # 1. Event list shows due reminders alert banner
        resp = self.client.get(reverse("events:list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Event Reminder")
        self.assertContains(resp, "Send All Due Reminders")

        # 2. Batch send due reminders
        send_resp = self.client.post(reverse("events:send_due_reminders"))
        self.assertEqual(send_resp.status_code, 302)
        event.refresh_from_db()
        self.assertTrue(event.reminder_sent)

        # 3. Resend individual reminder
        indiv_resp = self.client.post(reverse("events:send_reminder", kwargs={"pk": event.pk}))
        self.assertEqual(indiv_resp.status_code, 302)
        event.refresh_from_db()
        self.assertTrue(event.reminder_sent)
