from django.core.management.base import BaseCommand

from students.models import Student
from eligibility.models import EligibilityRecord
from eligibility.services import (
    calculate_student_eligibility,
    calculate_study_kit_eligibility,
    calculate_study_kit_continuation,
    calculate_laptop_eligibility,
)


class Command(BaseCommand):

    help = "Calculate student benefit eligibility"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=str,
            required=True,
            help="Academic year, for example 2026-27",
        )

    def handle(self, *args, **options):

        academic_year = options["year"]

        students = Student.objects.filter(
            status=Student.Status.ACTIVE
        )

        processed = 0

        # ----------------------------------------
        # BOOKS + WORKBOOK
        # ----------------------------------------
        for student in students:

            results = calculate_student_eligibility(
                student,
                academic_year
            )

            for result in results:

                EligibilityRecord.objects.update_or_create(
                    student=result.student,
                    benefit_type=result.benefit_type,
                    academic_year=result.academic_year,
                    defaults={
                        "eligible": result.eligible,
                        "selection_rank": result.selection_rank,
                        "reason": result.reason,
                    },
                )

                processed += 1

        # ----------------------------------------
        # STUDY KIT - TOP 10 CLASS 10
        # ----------------------------------------
        study_kit_count = calculate_study_kit_eligibility(
            academic_year=academic_year,
            limit=10,
        )

        # ----------------------------------------
        # STUDY KIT CONTINUATION
        # ----------------------------------------
        continued_count = calculate_study_kit_continuation(
            academic_year=academic_year,
        )

        # ----------------------------------------
        # LAPTOP - TOP 10 SECOND PUC
        # ----------------------------------------
        laptop_count = calculate_laptop_eligibility(
            academic_year=academic_year,
            limit=10,
        )

        # ----------------------------------------
        # FINAL RESULT
        # ----------------------------------------
        self.stdout.write(
            self.style.SUCCESS(
                f"Eligibility calculation completed. "
                f"{processed} basic records processed. "
                f"{study_kit_count} Class 10 students ranked for Study Kit. "
                f"{continued_count} previous Study Kit students continued. "
                f"{laptop_count} 2nd PUC students ranked for Laptop."
            )
        )
