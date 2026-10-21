import os
from django.core.management.base import BaseCommand, CommandError
from trackers.services.excel_importer import import_yfs_workbook


class Command(BaseCommand):
    help = "Imports, normalizes, and stores YFS Weekly Trackers and School Enrollment data from Excel files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to the .xlsx workbook file (e.g. Documentation/YfS-Aequs all Programme Weekly Tracker_2025-26 (1).xlsx)",
        )
        parser.add_argument(
            "--year",
            type=str,
            required=True,
            help="Academic Year (e.g. '2025-26' or '2026-27')",
        )
        parser.add_argument(
            "--ngo",
            type=str,
            default="YFS",
            help="Partner NGO code (e.g. 'YFS', 'AGASTYA', 'PRATHAM'). Default: 'YFS'",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        year = options["year"].strip()
        ngo_code = options.get("ngo", "YFS").strip()

        if not os.path.exists(file_path):
            raise CommandError(f"Excel workbook not found at '{file_path}'")

        self.stdout.write(self.style.NOTICE(f"Starting ingestion for Academic Year {year} (NGO: {ngo_code}) from: {file_path}"))

        try:
            res = import_yfs_workbook(file_path, year, ngo_code=ngo_code)
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n[OK] Successfully ingested {year} tracker:\n"
                    f"  - Sessions Created: {res['sessions_imported']:,}\n"
                    f"  - Class Enrollments: {res['enrollments_imported']:,}\n"
                    f"  - Total Exposures: {res['total_exposures']:,}\n"
                    f"  - Schools Linked/Created: {res['schools_count']:,}\n"
                )
            )
            self.stdout.write("Sheet Breakdown:")
            for sheet, stat in res.get("sheet_breakdown", {}).items():
                self.stdout.write(f"  • {sheet}: {stat}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to import tracker: {e}"))
            raise CommandError(str(e))
