import datetime
import io
import os
import pandas as pd
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from programs.models import NGO
from schools.models import School
from trackers.models import WeeklyTrackerSession, SchoolEnrollment, Programme
from trackers.filters import WeeklyTrackerSessionFilter
from trackers.services.excel_importer import (
    canonicalize_school_name,
    parse_academic_date,
    get_or_create_school_canonical,
    import_yfs_workbook,
)


class SchoolCanonicalizationTests(TestCase):
    def test_canonical_alias_mappings(self):
        self.assertEqual(canonicalize_school_name("uhps ymd"), "UHPS Yamakanamaradi")
        self.assertEqual(canonicalize_school_name("  UHPS YMD  "), "UHPS Yamakanamaradi")
        self.assertEqual(canonicalize_school_name("uemps ymd"), "UEMPS Yamakanamaradi")
        self.assertEqual(canonicalize_school_name("khpgs ymd"), "KHPGS Yamakanamaradi")
        self.assertEqual(canonicalize_school_name("khpgs yamkanamaradi"), "KHPGS Yamakanamaradi")
        self.assertEqual(canonicalize_school_name("khpbs ymd"), "KHPBS Yamakanamaradi")
        self.assertEqual(canonicalize_school_name("ghs hunoor mastiholi"), "GHS Hunnur Masthiholi")

    def test_get_or_create_school_canonical(self):
        cache = {}
        school1 = get_or_create_school_canonical("uhps ymd", cache)
        self.assertIsNotNone(school1)
        self.assertEqual(school1.name, "UHPS Yamakanamaradi")
        self.assertIn("uhps ymd", school1.code_aliases)

        # Re-fetch using standard name should not create duplicate
        school2 = get_or_create_school_canonical("UHPS Yamakanamaradi", cache)
        self.assertEqual(school1.pk, school2.pk)
        self.assertEqual(School.objects.count(), 1)


class AcademicDateParsingTests(TestCase):
    def test_first_half_of_academic_year(self):
        # June to December of 2025-26 should fall in 2025
        d_june, _, _ = parse_academic_date("June", 15, "2025-26")
        self.assertEqual(d_june, datetime.date(2025, 6, 15))

        d_dec, _, _ = parse_academic_date("December", 31, "2025-26")
        self.assertEqual(d_dec, datetime.date(2025, 12, 31))

        d_aug, _, _ = parse_academic_date("August", 10, "2026-27")
        self.assertEqual(d_aug, datetime.date(2026, 8, 10))

    def test_second_half_of_academic_year(self):
        # January to May of 2025-26 should fall in 2026
        d_jan, _, _ = parse_academic_date("January", 5, "2025-26")
        self.assertEqual(d_jan, datetime.date(2026, 1, 5))

        d_may, _, _ = parse_academic_date("May", 20, "2025-26")
        self.assertEqual(d_may, datetime.date(2026, 5, 20))

        d_feb, _, _ = parse_academic_date("February", 28, "2026-27")
        self.assertEqual(d_feb, datetime.date(2027, 2, 28))

    def test_invalid_dates_return_none(self):
        d_empty, _, _ = parse_academic_date("", 15, "2025-26")
        self.assertIsNone(d_empty)
        d_inv, _, _ = parse_academic_date("June", "invalid", "2025-26")
        self.assertIsNone(d_inv)
        d_not_month, _, _ = parse_academic_date("NotAMonth", 15, "2025-26")
        self.assertIsNone(d_not_month)


class WeeklyTrackerModelAndFilterTests(TestCase):
    def setUp(self):
        self.ngo = NGO.objects.create(name="Youth for Seva", code="YFS")
        self.school_a = School.objects.create(name="UHPS Yamakanamaradi", udise_code="UDISE-YMD-01", district="Belagavi")
        self.school_b = School.objects.create(name="GHS Hunnur Masthiholi", udise_code="UDISE-HUN-02", district="Belagavi")

        self.s1 = WeeklyTrackerSession.objects.create(
            ngo=self.ngo,
            academic_year="2025-26",
            programme=Programme.CHAAP_JR,
            session_date=datetime.date(2025, 7, 10),
            month_name="July",
            day_number=10,
            school=self.school_a,
            standard="5th",
            division="A",
            timing="10:00 - 11:00",
            topic="Fractions",
            instructor_name="Pooja Patil",
            session_type="Theory",
            boys_present=15,
            girls_present=18,
            total_exposures=33,
            teacher_present=True,
        )

        self.s2 = WeeklyTrackerSession.objects.create(
            ngo=self.ngo,
            academic_year="2025-26",
            programme=Programme.SEP,
            session_date=datetime.date(2025, 8, 15),
            month_name="August",
            day_number=15,
            school=self.school_b,
            standard="10th",
            division="B",
            timing="11:30 - 12:30",
            topic="English Grammar",
            instructor_name="Ramesh K",
            session_type="Practical",
            boys_present=20,
            girls_present=25,
            total_exposures=45,
            teacher_present=False,
        )

        self.s3 = WeeklyTrackerSession.objects.create(
            ngo=self.ngo,
            academic_year="2026-27",
            programme=Programme.IGNITE_BGM,
            session_date=datetime.date(2026, 9, 20),
            month_name="September",
            day_number=20,
            school=self.school_a,
            standard="8th",
            division="A",
            timing="02:00 - 03:00",
            topic="Robotics",
            instructor_name="Pooja Patil",
            session_type="Camp",
            boys_present=30,
            girls_present=20,
            total_exposures=50,
            teacher_present=True,
        )

    def test_filter_by_academic_year(self):
        f = WeeklyTrackerSessionFilter(
            {"academic_year": "2025-26"},
            queryset=WeeklyTrackerSession.objects.all(),
        )
        self.assertEqual(f.qs.count(), 2)

    def test_filter_by_programme(self):
        f = WeeklyTrackerSessionFilter(
            {"programme": Programme.CHAAP_JR},
            queryset=WeeklyTrackerSession.objects.all(),
        )
        self.assertEqual(f.qs.count(), 1)
        self.assertEqual(f.qs.first().pk, self.s1.pk)

    def test_filter_by_instructor(self):
        f = WeeklyTrackerSessionFilter(
            {"instructor_name": "Pooja"},
            queryset=WeeklyTrackerSession.objects.all(),
        )
        self.assertEqual(f.qs.count(), 2)

    def test_filter_by_date_range(self):
        f = WeeklyTrackerSessionFilter(
            {"date_from": "2025-07-01", "date_to": "2025-07-31"},
            queryset=WeeklyTrackerSession.objects.all(),
        )
        self.assertEqual(f.qs.count(), 1)
        self.assertEqual(f.qs.first().pk, self.s1.pk)

    def test_school_enrollment_unique_constraint(self):
        SchoolEnrollment.objects.create(
            ngo=self.ngo,
            academic_year="2025-26",
            programme=Programme.CHAAP_JR,
            school=self.school_a,
            standard="5th STD",
            boys=15,
            girls=18,
            total=33,
        )
        # Verify creating duplicate fails constraint
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SchoolEnrollment.objects.create(
                ngo=self.ngo,
                academic_year="2025-26",
                programme=Programme.CHAAP_JR,
                school=self.school_a,
                standard="5th STD",
                boys=20,
                girls=20,
                total=40,
            )


class TrackerViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.yfs = NGO.objects.create(name="Youth for Seva", code="YFS")
        self.agastya = NGO.objects.create(name="Agastya International Foundation", code="AGASTYA")
        self.pratham = NGO.objects.create(name="Pratham Foundation", code="PRATHAM")

        self.school_yfs = School.objects.create(name="UHPS Yamakanamaradi", udise_code="UDISE-YMD-VIEW", district="Belagavi")
        self.yfs.partner_schools.add(self.school_yfs)

        self.school_agastya = School.objects.create(name="GHS Mastiholi", udise_code="UDISE-MAS-VIEW", district="Belagavi")
        self.agastya.partner_schools.add(self.school_agastya)

        WeeklyTrackerSession.objects.create(
            ngo=self.yfs,
            academic_year="2025-26",
            programme=Programme.CHAAP_JR,
            session_date=datetime.date(2025, 6, 20),
            month_name="June",
            day_number=20,
            school=self.school_yfs,
            standard="4th",
            division="A",
            timing="09:00 - 10:00",
            topic="Intro",
            instructor_name="Anil M",
            session_type="Theory",
            boys_present=10,
            girls_present=12,
            total_exposures=22,
            teacher_present=True,
        )
        SchoolEnrollment.objects.create(
            ngo=self.yfs,
            academic_year="2025-26",
            programme=Programme.CHAAP_JR,
            school=self.school_yfs,
            standard="4th STD",
            boys=10,
            girls=12,
            total=22,
        )

    def test_session_list_view_default(self):
        response = self.client.get(reverse("trackers:session_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Youth for Seva")
        self.assertContains(response, "UHPS Yamakanamaradi")
        self.assertEqual(response.context["total_sessions"], 1)
        self.assertEqual(response.context["total_exposures"], 22)

    def test_ngo_session_list_separation(self):
        # YFS has 1 session, Agastya has 0 sessions (strict isolation)
        response_yfs = self.client.get(reverse("trackers:ngo_session_list", args=["yfs"]))
        self.assertEqual(response_yfs.status_code, 200)
        self.assertEqual(response_yfs.context["total_sessions"], 1)
        self.assertEqual(response_yfs.context["total_exposures"], 22)

        response_agastya = self.client.get(reverse("trackers:ngo_session_list", args=["agastya"]))
        self.assertEqual(response_agastya.status_code, 200)
        self.assertEqual(response_agastya.context["total_sessions"], 0)
        self.assertEqual(response_agastya.context["total_exposures"], 0)
        self.assertContains(response_agastya, "Agastya International Foundation")

    def test_ngo_enrollment_list_separation(self):
        # YFS has 1 enrollment, Agastya has 0 enrollments
        response_yfs = self.client.get(reverse("trackers:ngo_enrollment_list", args=["yfs"]))
        self.assertEqual(response_yfs.status_code, 200)
        self.assertEqual(response_yfs.context["total_students"], 22)
        self.assertContains(response_yfs, "4th STD")

        response_agastya = self.client.get(reverse("trackers:ngo_enrollment_list", args=["agastya"]))
        self.assertEqual(response_agastya.status_code, 200)
        self.assertEqual(response_agastya.context["total_students"], 0)
        self.assertContains(response_agastya, "Agastya International Foundation")

    def test_session_list_view_sorting(self):
        response = self.client.get(reverse("trackers:ngo_session_list", args=["yfs"]) + "?sort_by=-total_exposures")
        self.assertEqual(response.status_code, 200)

    def test_export_sessions_csv(self):
        response = self.client.get(reverse("trackers:ngo_export_csv", args=["yfs"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("Academic Year,Programme,Session Date", content)
        self.assertIn("UHPS Yamakanamaradi", content)

    def test_upload_view_get_renders_modal(self):
        response = self.client.get(reverse("trackers:ngo_upload_workbook", args=["yfs"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload Youth for Seva Tracker Excel")

    def test_upload_view_rejects_non_excel(self):
        fake_file = io.BytesIO(b"dummy text content")
        fake_file.name = "dummy.txt"
        response = self.client.post(
            reverse("trackers:ngo_upload_workbook", args=["yfs"]),
            {"file": fake_file, "academic_year": "2025-26", "ngo_code": "YFS"},
            follow=True,
        )
        self.assertContains(response, "Only Microsoft Excel (.xlsx/.xls) files are supported.")


class ManagementCommandAndIdempotencyTests(TestCase):
    def test_management_command_execution(self):
        file_path = "Documentation/YFS-Aequs all Programme Weekly Tracker_2026-27.xlsx"
        if not os.path.exists(file_path):
            self.skipTest(f"{file_path} not found in workspace.")

        out = io.StringIO()
        call_command("import_yfs_trackers", file=file_path, year="2026-27", stdout=out)
        output = out.getvalue()
        self.assertIn("Successfully ingested 2026-27 tracker", output)

        initial_count = WeeklyTrackerSession.objects.filter(academic_year="2026-27").count()
        self.assertGreater(initial_count, 0)

        # Re-run management command to test idempotency
        out2 = io.StringIO()
        call_command("import_yfs_trackers", file=file_path, year="2026-27", stdout=out2)
        second_count = WeeklyTrackerSession.objects.filter(academic_year="2026-27").count()

        # Row counts must match exactly, no duplicate accumulation
        self.assertEqual(initial_count, second_count)


class FoundationTabsIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin = User.objects.create_superuser("testadmin", "admin@test.com", "pass123")
        self.client.force_login(self.admin)
        self.yfs, _ = NGO.objects.get_or_create(code="YFS", defaults={"name": "Youth for Seva"})
        self.agastya, _ = NGO.objects.get_or_create(code="AGASTYA", defaults={"name": "Agastya Foundation"})
        self.pratham, _ = NGO.objects.get_or_create(code="PRATHAM", defaults={"name": "Pratham Foundation"})
        self.school_yfs = School.objects.create(name="UHPS Yamakanamaradi", udise_code="UDISE-YMD-VIEW", district="Belagavi")
        self.yfs.partner_schools.add(self.school_yfs)
        SchoolEnrollment.objects.create(
            ngo=self.yfs,
            academic_year="2025-26",
            programme="CHAAP_JR",
            school=self.school_yfs,
            standard="4th STD",
            boys=10,
            girls=12,
            total=22,
        )

    def test_sidebar_excludes_standalone_dropdown_trackers(self):
        response = self.client.get(reverse("schools:portal_yfs"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Ensure dropdownTrackers is removed from the sidebar
        self.assertNotIn('id="dropdownTrackers"', content)
        # Ensure Foundation Schools contains YFS
        self.assertIn('Youth for Seva Schools &amp; Weekly Trackers', content)

    def test_schools_portal_includes_foundation_tabs(self):
        response = self.client.get(reverse("schools:portal_yfs"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["foundation_subtab"], "schools")
        content = response.content.decode("utf-8")
        self.assertIn("FOUNDATION PARTNERS:", content)
        self.assertIn("Weekly Tracker", content)
        self.assertIn("Class Enrollments", content)

    def test_tab_param_redirects_to_trackers_and_enrollments(self):
        # Redirect tab=trackers to ngo_session_list
        res_trackers = self.client.get(reverse("schools:portal_yfs") + "?tab=trackers")
        self.assertEqual(res_trackers.status_code, 302)
        self.assertEqual(res_trackers.url, reverse("trackers:ngo_session_list", args=["yfs"]))

        # Redirect tab=enrollments to ngo_enrollment_list
        res_enrollments = self.client.get(reverse("schools:portal_yfs") + "?tab=enrollments")
        self.assertEqual(res_enrollments.status_code, 302)
        self.assertEqual(res_enrollments.url, reverse("trackers:ngo_enrollment_list", args=["yfs"]))

    def test_session_list_has_foundation_tabs(self):
        response = self.client.get(reverse("trackers:ngo_session_list", args=["yfs"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["foundation_subtab"], "trackers")
        content = response.content.decode("utf-8")
        self.assertIn("FOUNDATION PARTNERS:", content)
        self.assertIn("tab-trackers active", content)

    def test_get_ngo_enrollment_roster_pivoting(self):
        from trackers.roster import get_ngo_enrollment_roster
        roster = get_ngo_enrollment_roster(self.yfs, academic_year="2025-26")
        self.assertIsNotNone(roster)
        self.assertEqual(len(roster["schools"]), 1)
        sc = roster["schools"][0]
        self.assertEqual(sc["name"], "UHPS Yamakanamaradi")
        self.assertEqual(sc["divisions"][0]["c4"], [10, 12, 22])
        self.assertEqual(sc["divisions"][0]["gt"], [10, 12, 22])
        self.assertEqual(roster["kpis"]["total_schools"], 1)
        self.assertEqual(roster["kpis"]["total_students"], 22)

    def test_enrollment_list_renders_spreadsheet_view(self):
        response = self.client.get(reverse("trackers:ngo_enrollment_list", args=["yfs"]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("roster_data", response.context)
        content = response.content.decode("utf-8")
        self.assertIn("School Profile &amp; Participating Schools Roster", content)
        self.assertIn("Matrix Table", content)
        self.assertIn("Taluk Filter:", content)
        self.assertIn("UHPS Yamakanamaradi", content)
        self.assertIn("rosterMainTable", content)
        self.assertIn("rosterSpreadsheetView", content)
        self.assertIn("rosterCardsView", content)

    def test_schools_portal_renders_directory_view(self):
        response = self.client.get(reverse("schools:portal_yfs"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Partner School Directory", content)
        self.assertIn("portalSchoolCardsWrapper", content)
        self.assertIn("portalSchoolTableWrapper", content)
        self.assertNotIn("rosterSpreadsheetView", content)

    def test_program_roster_fallback_for_ngo_programs(self):
        from programs.models import Program, Project
        from programs.roster import get_program_school_roster
        proj = Project.objects.create(name="STEAM Test Project", ngo=self.yfs)
        prog = Program.objects.create(
            title="MSL Test Program",
            code="PRG-TEST-MSL-01",
            project=proj,
            ngo=self.yfs,
            academic_year="2025-26"
        )
        roster = get_program_school_roster(prog)
        self.assertIsNotNone(roster)
        self.assertEqual(len(roster["schools"]), 1)
        self.assertEqual(roster["schools"][0]["name"], "UHPS Yamakanamaradi")


