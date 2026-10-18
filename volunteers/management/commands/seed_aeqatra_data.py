from django.core.management.base import BaseCommand
from datetime import date, timedelta
from volunteers.models import Volunteer, VolunteerActivity, EmployeeTestimonial


class Command(BaseCommand):
    help = "Seeds AEQATRA employee volunteering activities and video testimonials."

    def handle(self, *args, **options):
        # Ensure at least one volunteer exists
        vol = Volunteer.objects.first()
        if not vol:
            vol = Volunteer.objects.create(
                first_name="Rohit",
                last_name="Patil",
                email="rohit.patil@aequs.com",
                phone="+91 98451 22340",
                occupation="Senior CNC Tooling Specialist",
                city="Belagavi",
                status="ACTIVE",
            )

        # Seed activities if empty
        if not VolunteerActivity.objects.exists():
            activities = [
                # Completed
                ("STEM Lab Mentorship Drive - Hattargi", date(2026, 8, 15), "COMPLETED", "Volunteers assisted instructors in conducting physics and optics experiments for 120 Class 9 students."),
                ("One Precious Notebook Distribution - Belagavi Rural", date(2026, 9, 5), "COMPLETED", "Distributed 3,400 notebooks across 12 government primary and high schools."),
                # Ongoing
                ("Aerospace Clean Tech Awareness Workshop", date(2026, 10, 2), "ONGOING", "Active multi-week workshops introducing students to green energy and sustainable aerospace design."),
                ("SSLC Math & Science Revision Camps - Hubballi", date(2026, 10, 10), "ONGOING", "Weekend preparatory classes for upcoming board exam students."),
                # Upcoming
                ("Avishkar Science Fair Volunteer Judging Panel", date(2026, 11, 14), "ASSIGNED", "Mentoring student science model exhibits and evaluating regional school teams."),
                ("Aequs Foundation Green Campus Tree Plantation", date(2026, 12, 5), "ASSIGNED", "Planting 500 indigenous fruit-bearing trees across adopted school grounds in Hukkeri."),
            ]
            for title, dt, status, desc in activities:
                VolunteerActivity.objects.create(
                    volunteer=vol,
                    activity_name=title,
                    activity_date=dt,
                    status=status,
                    description=desc,
                )
            self.stdout.write(self.style.SUCCESS(f"Created {len(activities)} AEQATRA volunteer activities."))

        # Seed testimonials if empty
        if not EmployeeTestimonial.objects.exists():
            testimonials = [
                (
                    "Rohit Patil",
                    "Senior CNC Tooling Specialist",
                    "Aerospace Machining Division",
                    "Belagavi SEZ",
                    "Teaching high school students robotics and hands-on manufacturing at the Science Centre showed me how our everyday engineering skills can ignite young minds.",
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                ),
                (
                    "Priyanka Kulkarni",
                    "Quality Assurance Lead",
                    "Precision Aerospace Parts",
                    "Belagavi SEZ",
                    "Volunteering with the Aequs Foundation for the Mobile Science Lab allowed us to bring real aerospace precision parts to rural classrooms. The excitement on students' faces was unforgettable.",
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                ),
                (
                    "Anand Hiremath",
                    "Production Supervisor",
                    "Tool & Die Division",
                    "Hubballi Hub",
                    "Through AEQATRA, our team has dedicated over 40 hours to student mentoring. Giving back through STEM education is one of the most rewarding parts of working at Aequs.",
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                ),
            ]
            for name, role, dept, loc, quote, url in testimonials:
                EmployeeTestimonial.objects.create(
                    employee_name=name,
                    employee_role=role,
                    department=dept,
                    plant_location=loc,
                    quote=quote,
                    video_url=url,
                    academic_year="2026-27",
                    is_featured=True,
                )
            self.stdout.write(self.style.SUCCESS(f"Created {len(testimonials)} AEQATRA employee video testimonials."))
