"""
Django management command: cleanup_eligibility

WHERE TO PUT THIS FILE:
    eligibility/management/commands/cleanup_eligibility.py

    (create the 'management' and 'commands' folders if they don't exist,
    each needs an empty __init__.py file inside it, i.e.:
        eligibility/management/__init__.py
        eligibility/management/commands/__init__.py
        eligibility/management/commands/cleanup_eligibility.py   <- this file
    )

HOW TO RUN (works identically in PowerShell, cmd, bash, macOS, Linux):

    python manage.py cleanup_eligibility

    Add --dry-run to only preview what would change, without saving:

    python manage.py cleanup_eligibility --dry-run

    Add --delete to hard-delete bad records instead of deactivating them:

    python manage.py cleanup_eligibility --delete
"""

from django.core.management.base import BaseCommand
from eligibility.models import EligibilityRecord, BenefitType
from eligibility.services import get_latest_academic_record, parse_class_number


class Command(BaseCommand):
    help = "One-time cleanup of bad Books/Workbook eligibility records caused by the parse_class_number() bug."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would be changed, without saving anything.",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Hard-delete bad records instead of marking them ineligible.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        delete_instead = options["delete"]

        affected_types = [BenefitType.BOOK, BenefitType.WORKBOOK]

        qs = EligibilityRecord.objects.filter(
            benefit_type__in=affected_types,
            eligible=True,
        ).select_related("student")

        bad_records = []

        for rec in qs:
            student = rec.student
            academic_record = get_latest_academic_record(student, rec.academic_year)
            course_text = (
                academic_record.class_or_course if academic_record else student.current_class
            )
            class_num = parse_class_number(course_text)

            is_valid = False
            if rec.benefit_type == BenefitType.BOOK:
                is_valid = class_num is not None and 1 <= class_num <= 10
            elif rec.benefit_type == BenefitType.WORKBOOK:
                is_valid = class_num == 10

            if not is_valid:
                bad_records.append((rec, course_text))

        self.stdout.write(f"Found {len(bad_records)} bad eligibility record(s):\n")
        for rec, course_text in bad_records:
            self.stdout.write(
                f"  - {rec.student.student_name} "
                f"({rec.student.admission_number}) | "
                f"benefit={rec.get_benefit_type_display()} | "
                f"course='{course_text}' | "
                f"current reason='{rec.reason}'"
            )

        if not bad_records:
            self.stdout.write(self.style.SUCCESS("Nothing to fix."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("\n--dry-run set: no changes saved."))
            return

        for rec, course_text in bad_records:
            if delete_instead:
                rec.delete()
            else:
                rec.eligible = False
                rec.reason = (
                    f"[Auto-corrected] Not eligible — '{course_text}' is not a "
                    f"Class 1-10 school standard. Previous reason: {rec.reason}"
                )
                rec.save()

        action = "Deleted" if delete_instead else "Deactivated"
        self.stdout.write(self.style.SUCCESS(f"\n{action} {len(bad_records)} record(s)."))