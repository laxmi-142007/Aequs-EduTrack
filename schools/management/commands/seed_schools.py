from django.core.management.base import BaseCommand
from schools.models import School, SchoolMilestone, SchoolResource, GradeStrength
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Seed initial government school data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Government School data...")

        # Ensure demo admin user exists
        admin_user, created = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True})
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created demo admin user (admin / admin123)"))

        # School 1
        s1, created = School.objects.get_or_create(
            udise_code="29010200301",
            defaults={
                "name": "Govt. Model High School",
                "district": "Bangalore Urban",
                "taluk": "South",
                "village": "Jayanagar",
                "pincode": "560041",
                "address": "7th Main, 4th Block, Jayanagar, Bangalore",
                "phone": "+91 98765 43210",
                "email": "info@govtmodelhigh.edu.in",
                "website": "https://govtmodelhigh.edu.in",
                "headmaster_name": "Dr. Ramesh Kumar",
                "headmaster_phone": "+91 98450 12345",
                "headmaster_qualification": "M.Sc., M.Ed., Ph.D.",
                "headmaster_experience": 18,
                "affiliation": "State",
                "established_year": 1985,
                "status": School.Status.ACTIVE,
            }
        )
        if created or not s1.grade_strengths.exists():
            grades = [
                ("Nursery", 120, 135, "+15", 1),
                ("Class 1", 250, 245, "+5", 2),
                ("Class 2", 260, 265, "+10", 3),
                ("Class 3", 240, 230, "-5", 4),
                ("Class 4", 220, 215, "0", 5),
                ("Class 5", 200, 190, "-15", 6),
                ("Class 6 - 12", 350, 320, "+20", 7),
            ]
            s1.grade_strengths.all().delete()
            total_st = 0
            for g_name, m, f, ch, ord_idx in grades:
                tot = m + f
                total_st += tot
                GradeStrength.objects.create(
                    school=s1,
                    grade_level=g_name,
                    male_students=m,
                    female_students=f,
                    total_students=tot,
                    change_vs_last_year=ch,
                    order=ord_idx
                )
            s1.student_strength = total_st
            s1.save()

            s1.milestones.all().delete()
            SchoolMilestone.objects.create(
                school=s1,
                title="Completion of New Wing (2020)",
                year_or_date="2020",
                details="Increased capacity from 500 to 800 students.",
                impact="Improved infrastructure and learning environment."
            )
            SchoolMilestone.objects.create(
                school=s1,
                title="Sworn-in Ceremony of New Principal (2023)",
                year_or_date="2023",
                details="Introduction of modern pedagogical tools and curriculum updates.",
                impact="Elevated teaching standards and community engagement."
            )

            s1.resources.all().delete()
            SchoolResource.objects.create(
                school=s1,
                resource_name="Mid-Day Meal Provisions",
                status="Active",
                quantity=1,
                last_updated_note="October 2023",
                details="Hot cooked meals provided daily to all enrolled students."
            )
            SchoolResource.objects.create(
                school=s1,
                resource_name="Digital Smart Classroom Kits (x3)",
                status="Delivered",
                quantity=3,
                last_updated_note="August 2023",
                details="Smart interactive touchboards and digital audio systems."
            )

        # School 2
        s2, created = School.objects.get_or_create(
            udise_code="29010200455",
            defaults={
                "name": "Govt. Higher Secondary School, Belagavi",
                "district": "Belagavi",
                "taluk": "Belagavi North",
                "village": "Kakati",
                "pincode": "591113",
                "address": "NH 4, Kakati, Belagavi",
                "phone": "+91 831 2456789",
                "email": "principal@ghsskakati.edu.in",
                "website": "https://ghsskakati.edu.in",
                "headmaster_name": "Smt. Sunita Patil",
                "headmaster_phone": "+91 94481 98765",
                "headmaster_qualification": "M.A., B.Ed.",
                "headmaster_experience": 14,
                "affiliation": "State",
                "established_year": 1994,
                "status": School.Status.ACTIVE,
            }
        )
        if created or not s2.grade_strengths.exists():
            grades2 = [
                ("Nursery", 90, 95, "+10", 1),
                ("Class 1", 180, 190, "+8", 2),
                ("Class 2", 195, 200, "+12", 3),
                ("Class 3", 175, 180, "-2", 4),
                ("Class 4", 160, 170, "+4", 5),
                ("Class 5", 150, 155, "-5", 6),
                ("Class 6 - 12", 280, 310, "+25", 7),
            ]
            s2.grade_strengths.all().delete()
            total_st2 = 0
            for g_name, m, f, ch, ord_idx in grades2:
                tot = m + f
                total_st2 += tot
                GradeStrength.objects.create(
                    school=s2,
                    grade_level=g_name,
                    male_students=m,
                    female_students=f,
                    total_students=tot,
                    change_vs_last_year=ch,
                    order=ord_idx
                )
            s2.student_strength = total_st2
            s2.save()

            s2.milestones.all().delete()
            SchoolMilestone.objects.create(
                school=s2,
                title="Science & Robotics Lab Inauguration (2022)",
                year_or_date="2022",
                details="State-of-the-art STEM equipment donated by EduTrack partnership.",
                impact="Over 400 high school students trained in practical electronics."
            )
            s2.resources.all().delete()
            SchoolResource.objects.create(
                school=s2,
                resource_name="Aequs STEM Educational Kits",
                status="Delivered",
                quantity=15,
                last_updated_note="January 2024",
                details="Full robotics and physics experimentation sets."
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded government schools!"))
