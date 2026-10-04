from django.core.management.base import BaseCommand
from decimal import Decimal
from datetime import date
from programs.models import MikePropenScholarshipApplication
from schools.models import School
from students.models import Student


class Command(BaseCommand):
    help = "Seeds sample Mike Propen Scholarship applications for Analysis and Data Details."

    def handle(self, *args, **options):
        if MikePropenScholarshipApplication.objects.exists():
            self.stdout.write("Mike Propen Scholarship applications already exist.")
            return

        school1 = School.objects.first()
        student1 = Student.objects.first()

        sample_applicants = [
            ("Aishwarya Kulkarni", "FEMALE", "Class 10", 94.50, Decimal("85000.00"), "+91 98451 11201", "aishwarya.k@example.com", "Aspiring aerospace materials researcher seeking merit assistance.", Decimal("30000.00"), "AWARDED", "2026-27", date(2026, 7, 10), date(2026, 8, 1)),
            ("Basavaraj Hatti", "MALE", "Class 10", 91.20, Decimal("72000.00"), "+91 98451 11202", "basavaraj.h@example.com", "Top ranker in rural block mathematics olympiad, pursuing polytechnic diploma.", Decimal("25000.00"), "DISBURSED", "2026-27", date(2026, 7, 12), date(2026, 8, 15)),
            ("Sneha Patil", "FEMALE", "1st PUC", 96.00, Decimal("90000.00"), "+91 98451 11203", "sneha.patil@example.com", "Physics Olympiad finalist, daughter of small-scale artisan.", Decimal("35000.00"), "AWARDED", "2026-27", date(2026, 7, 15), None),
            ("Kavita Kamble", "FEMALE", "Class 10", 88.40, Decimal("60000.00"), "+91 98451 11204", "kavita.k@example.com", "First generation learner from government rural high school.", Decimal("25000.00"), "UNDER_REVIEW", "2026-27", date(2026, 8, 1), None),
            ("Manjunath Pujar", "MALE", "2nd PUC", 89.80, Decimal("95000.00"), "+91 98451 11205", "manjunath.p@example.com", "Aspires to join aeronautical engineering degree program at Belagavi.", Decimal("30000.00"), "INTERVIEW_SCHEDULED", "2026-27", date(2026, 8, 10), None),
            ("Deepa Narvekar", "FEMALE", "Class 10", 87.00, Decimal("65000.00"), "+91 98451 11206", "deepa.n@example.com", "State level junior science exhibition winner.", Decimal("25000.00"), "SUBMITTED", "2026-27", date(2026, 9, 2), None),
            ("Vinayak Naik", "MALE", "Class 10", 92.60, Decimal("80000.00"), "+91 98451 11207", "vinayak.n@example.com", "Consistent school academic topper, passionate about computer algorithms.", Decimal("25000.00"), "AWARDED", "2025-26", date(2025, 7, 14), date(2025, 8, 10)),
            ("Megha Badiger", "FEMALE", "1st PUC", 90.10, Decimal("70000.00"), "+91 98451 11208", "megha.b@example.com", "Merit student continuing higher secondary education in science stream.", Decimal("25000.00"), "DISBURSED", "2025-26", date(2025, 7, 20), date(2025, 8, 25)),
        ]

        for name, gender, grade, pct, inc, phone, email, sop, amt, status, ay, app_dt, disb_dt in sample_applicants:
            MikePropenScholarshipApplication.objects.create(
                student=student1 if name == "Aishwarya Kulkarni" else None,
                student_name=name,
                gender=gender,
                school=school1,
                school_name=school1.name if school1 else "Govt Model High School, Hattargi",
                grade_level=grade,
                academic_percentage=Decimal(str(pct)),
                annual_family_income=inc,
                contact_phone=phone,
                email=email,
                statement_of_purpose=sop,
                scholarship_amount=amt,
                status=status,
                academic_year=ay,
                application_date=app_dt,
                disbursement_date=disb_dt,
            )

        self.stdout.write(self.style.SUCCESS(f"Created {len(sample_applicants)} Mike Propen Scholarship applications."))
