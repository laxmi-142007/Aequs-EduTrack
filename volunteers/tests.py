from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import date

from events.models import Event
from volunteers.models import Volunteer, VolunteerFormLink, EventParticipation


class EventVolunteerRegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.event_a = Event.objects.create(
            title="STEM Science Fair 2026",
            event_type=Event.EventType.EVENT,
            status=Event.Status.PLANNED,
            event_date=date(2026, 11, 15),
            location="Belagavi Main Campus",
            organizer="Dr. Patil",
        )
        self.event_b = Event.objects.create(
            title="Annual Clean Campus Drive",
            event_type=Event.EventType.CAMPAIGN,
            status=Event.Status.PLANNED,
            event_date=date(2026, 12, 1),
            location="SEZ Plant 2",
            organizer="Pooja K.",
        )

    def test_generate_event_specific_form_link_json(self):
        """API should generate a form link bound to a specific event."""
        url = reverse("volunteers:generate_form_link_json")
        response = self.client.get(f"{url}?event_id={self.event_a.id}&role=Lead Mentor")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["event_id"], self.event_a.id)
        self.assertEqual(data["event_title"], self.event_a.title)
        self.assertEqual(data["role"], "Lead Mentor")

        link = VolunteerFormLink.objects.get(token=data["token"])
        self.assertEqual(link.event, self.event_a)
        self.assertEqual(link.role, "Lead Mentor")

    def test_event_form_page_renders_event_context(self):
        """Public volunteer form should display target event details when accessed with an event-bound token."""
        form_link = VolunteerFormLink.objects.create(event=self.event_a, role="STEM Judge")
        url = reverse("volunteers:public_form_by_token", kwargs={"token": form_link.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "STEM Science Fair 2026")
        self.assertContains(response, "Belagavi Main Campus")
        self.assertContains(response, "STEM Judge")
        self.assertContains(response, "Register & Enroll for STEM Science Fair 2026")

    def test_submission_enrolls_volunteer_exclusively_for_target_event(self):
        """Submitting an event volunteer form should enroll the volunteer ONLY for that particular event."""
        form_link = VolunteerFormLink.objects.create(event=self.event_a, role="Workshop Facilitator")
        url = reverse("volunteers:public_form_by_token", kwargs={"token": form_link.token})

        post_data = {
            "first_name": "Arjun",
            "last_name": "Kulkarni",
            "email": "arjun.kulkarni@aequs.com",
            "phone": "9876543210",
            "employee_code": "AEQ-5521",
            "department": "Aerospace Machining",
            "plant_location": "Belagavi SEZ",
            "academic_year": "2026-27",
            "gender": "M",
            "skills": "Robotics, 3D Printing",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"event_id={self.event_a.id}", response.url)

        # Volunteer profile created
        vol = Volunteer.objects.get(email="arjun.kulkarni@aequs.com")
        self.assertEqual(vol.first_name, "Arjun")
        self.assertEqual(vol.employee_code, "AEQ-5521")
        self.assertTrue(vol.is_employee)

        # Enrolled specifically for Event A
        participation_a = EventParticipation.objects.filter(volunteer=vol, event=self.event_a)
        self.assertEqual(participation_a.count(), 1)
        part = participation_a.first()
        self.assertEqual(part.role, "Workshop Facilitator")
        self.assertEqual(part.participation_status, "REQUESTED")

        # Must NOT be enrolled in Event B
        participation_b = EventParticipation.objects.filter(volunteer=vol, event=self.event_b)
        self.assertEqual(participation_b.count(), 0)

    def test_existing_volunteer_can_register_for_new_event_without_duplicate_error(self):
        """If a volunteer already exists in the system, submitting an event form links them to the new event cleanly."""
        vol = Volunteer.objects.create(
            first_name="Sunita",
            last_name="Desai",
            email="sunita.desai@aequs.com",
            phone="9123456780",
            employee_code="AEQ-3310",
            department="Quality Assurance",
            status="ACTIVE",
        )

        form_link = VolunteerFormLink.objects.create(event=self.event_b, role="Drive Coordinator")
        url = reverse("volunteers:public_form_by_token", kwargs={"token": form_link.token})

        post_data = {
            "first_name": "Sunita",
            "last_name": "Desai",
            "email": "sunita.desai@aequs.com",
            "phone": "9123456780",
            "employee_code": "AEQ-3310",
            "department": "Quality Assurance",
            "plant_location": "SEZ Plant 2",
            "academic_year": "2026-27",
            "gender": "F",
            "skills": "Logistics",
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Enrolled for {self.event_b.title}!")

        # Volunteer count must still be 1 (no duplicate)
        self.assertEqual(Volunteer.objects.filter(email="sunita.desai@aequs.com").count(), 1)

        # Enrolled specifically for Event B
        part_b = EventParticipation.objects.filter(volunteer=vol, event=self.event_b)
        self.assertEqual(part_b.count(), 1)
        self.assertEqual(part_b.first().role, "Drive Coordinator")

        # Still not enrolled in Event A
        self.assertEqual(EventParticipation.objects.filter(volunteer=vol, event=self.event_a).count(), 0)

    def test_registration_success_page_displays_event_details(self):
        """The success page should display event details when event_id is supplied."""
        url = reverse("volunteers:registration_success")
        response = self.client.get(f"{url}?event_id={self.event_a.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Enrolled for {self.event_a.title}!")
        self.assertContains(response, "Event Participation Summary")
        self.assertContains(response, self.event_a.location)

    def test_qr_endpoints_by_pk_and_token(self):
        """Both /volunteers/form/qr/<pk>/ and /volunteers/form/qr/<token>/ return a valid PNG image."""
        link = VolunteerFormLink.objects.create(event=self.event_a, role="Volunteer")
        res_pk = self.client.get(f"/volunteers/form/qr/{link.pk}/")
        self.assertEqual(res_pk.status_code, 200)
        self.assertEqual(res_pk["Content-Type"], "image/png")

        res_token = self.client.get(f"/volunteers/form/qr/{link.token}/")
        self.assertEqual(res_token.status_code, 200)
        self.assertEqual(res_token["Content-Type"], "image/png")

    def test_form_success_and_public_urls_resolve_cleanly(self):
        """Direct access to /volunteers/form/success/ and /volunteers/form/public/ must return 200."""
        res_success = self.client.get("/volunteers/form/success/")
        self.assertEqual(res_success.status_code, 200)

        res_public = self.client.get("/volunteers/form/public/")
        self.assertEqual(res_public.status_code, 200)

    def test_journey_lookup_by_employee_code(self):
        """Employee can lookup their volunteering journey by Employee Code."""
        vol = Volunteer.objects.create(
            first_name="Priyanka",
            last_name="Kulkarni",
            email="priyanka.k@aequs.com",
            phone="9845012345",
            employee_code="AEQ-2015",
            department="Quality Assurance",
            status="ACTIVE",
        )
        EventParticipation.objects.create(
            volunteer=vol,
            event=self.event_a,
            role="Lead Judge",
            participation_status="ATTENDED",
            hours_contributed=12.5,
        )

        url = reverse("volunteers:journey_lookup")
        response = self.client.get(f"{url}?q=AEQ-2015")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["volunteer"]["name"], "Priyanka Kulkarni")
        self.assertEqual(data["volunteer"]["employee_code"], "AEQ-2015")
        self.assertEqual(data["volunteer"]["total_hours"], 12.5)
        self.assertEqual(data["volunteer"]["events_count"], 1)
        self.assertEqual(len(data["volunteer"]["timeline"]), 1)
        self.assertEqual(data["volunteer"]["timeline"][0]["title"], self.event_a.title)
        self.assertEqual(data["volunteer"]["timeline"][0]["hours"], 12.5)

    def test_journey_lookup_by_pk(self):
        """Endpoint /volunteers/<pk>/journey-json/ returns the volunteer's journey details."""
        vol = Volunteer.objects.create(
            first_name="Rohit",
            last_name="Patil",
            email="rohit.p@aequs.com",
            phone="9845098765",
            employee_code="AEQ-3088",
            department="Aerospace Machining",
            status="ACTIVE",
        )
        url = reverse("volunteers:journey_lookup_by_pk", kwargs={"pk": vol.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["volunteer"]["employee_code"], "AEQ-3088")

    def test_journey_lookup_not_found(self):
        """Looking up a non-existent employee ID returns 404 with helpful error message."""
        url = reverse("volunteers:journey_lookup")
        response = self.client.get(f"{url}?q=AEQ-99999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("No employee volunteer found matching 'AEQ-99999'", data["message"])

    def test_top_10_volunteers_leaderboard_in_list_view(self):
        """Top 10 Volunteers Leaderboard ranks volunteers by contributed hours descending."""
        vol1 = Volunteer.objects.create(first_name="Vol", last_name="One", email="v1@a.com", phone="111", employee_code="AEQ-01", status="ACTIVE")
        vol2 = Volunteer.objects.create(first_name="Vol", last_name="Two", email="v2@a.com", phone="222", employee_code="AEQ-02", status="ACTIVE")

        EventParticipation.objects.create(volunteer=vol1, event=self.event_a, hours_contributed=25.0)
        EventParticipation.objects.create(volunteer=vol2, event=self.event_a, hours_contributed=10.0)

        url = reverse("volunteers:list")
        response = self.client.get(f"{url}?ay=2026-27")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Top 10 CSR Champions / Volunteers")
        self.assertContains(response, "Check Journey by ID")
        top_vols = response.context["top_volunteers"]
        self.assertGreaterEqual(len(top_vols), 2)
        # vol1 should rank higher than vol2 due to 25.0 > 10.0 hours
        self.assertEqual(top_vols[0].id, vol1.id)
        self.assertEqual(top_vols[0].total_hours, 25.0)
        self.assertEqual(top_vols[1].id, vol2.id)
        self.assertEqual(top_vols[1].total_hours, 10.0)

