from django.core.management.base import BaseCommand

from students.models import Student

from eligibility.services import (
    generate_student_eligibility,
    generate_study_kit_eligibility,
    generate_laptop_eligibility,
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
        # BOOKS + WORKBOOK + CONTINUATION + INTERNSHIP
        # ----------------------------------------

        for student in students:

            results = generate_student_eligibility(
                student=student,
                academic_year=academic_year,
            )

            processed += len(results)

        # ----------------------------------------
        # STUDY KIT - TOP 10 CLASS 10
        # ----------------------------------------

        generate_study_kit_eligibility(
            academic_year=academic_year
        )

        # ----------------------------------------
        # LAPTOP - TOP 10 SECOND PUC
        # ----------------------------------------

        generate_laptop_eligibility(
            academic_year=academic_year
        )

        # ----------------------------------------
        # FINAL RESULT
        # ----------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                f"Eligibility calculation completed successfully. "
                f"{processed} individual eligibility records processed. "
                f"Study Kit and Laptop rankings generated for "
                f"{academic_year}."
            )
        )
