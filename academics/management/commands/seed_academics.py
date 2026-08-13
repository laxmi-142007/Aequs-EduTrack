from decimal import Decimal
from django.core.management.base import BaseCommand
from academics.models import AcademicRecord
from students.models import Student
from schools.models import School


class Command(BaseCommand):
    help = "Seed initial academic records"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Academic Records...")

        school, _ = School.objects.get_or_create(
            udise_code="29010200301",
            defaults={"name": "Govt. Model High School", "district": "Bangalore Urban", "village": "Jayanagar"}
        )

        sample_data = [
            {"name": "Aarav Sharma", "adm": "ADM-2023-001", "year": "2023-2024", "class": "Class 5", "pct": 92.5, "rank": 1, "status": "Promoted", "transfer": ""},
            {"name": "Diya Patel", "adm": "ADM-2023-002", "year": "2023-2024", "class": "Class 5", "pct": 88.0, "rank": 3, "status": "Promoted", "transfer": ""},
            {"name": "Rohan Gupta", "adm": "ADM-2023-003", "year": "2023-2024", "class": "Class 5", "pct": 45.0, "rank": 32, "status": "Conditional", "transfer": ""},
            {"name": "Sanya Iyer", "adm": "ADM-2023-004", "year": "2023-2024", "class": "Class 5", "pct": 32.0, "rank": 40, "status": "Not Promoted", "transfer": ""},
        ]

        for item in sample_data:
            st, _ = Student.objects.get_or_create(
                admission_number=item["adm"],
                defaults={
                    "student_name": item["name"],
                    "school": school,
                    "current_class": item["class"],
                    "gender": Student.Gender.MALE if "Sharma" in item["name"] or "Gupta" in item["name"] else Student.Gender.FEMALE,
                    "parent_name": "Parent of " + item["name"],
                }
            )
            AcademicRecord.objects.get_or_create(
                student=st,
                academic_year=item["year"],
                class_or_course=item["class"],
                defaults={
                    "percentage": Decimal(str(item["pct"])),
                    "rank": item["rank"],
                    "promotion_status": item["status"],
                    "transfer_school": item["transfer"],
                }
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded academic records!"))
