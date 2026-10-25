from pathlib import Path
from django.core.management import call_command
from django.core.management.base import BaseCommand
from accounts.models import User
from schools.models import School
from students.models import Student


class Command(BaseCommand):
    help = "Loads complete baseline seed data (students, schools, programs, scholarships, etc.) into the database if empty or forced."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reload fixture even if database already has students/schools",
        )
        parser.add_argument(
            "--fixture",
            type=str,
            default="",
            help="Custom fixture file path (defaults to fixtures/seed_data.json or seed_data.json)",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        custom_fixture = options.get("fixture", "").strip()

        # 1. Ensure permission groups and admin users exist first
        try:
            call_command("setup_groups", verbosity=0)
            call_command("create_default_admin", verbosity=0)
            call_command("seed_dhaval_admin", verbosity=0)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Note during admin/group setup: {e}"))

        # 2. Check if data should be loaded
        student_count = Student.objects.count()
        school_count = School.objects.count()

        if not force and student_count > 0 and school_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Database already populated: {student_count} students and {school_count} schools present. Skipping seed fixture load (use --force to reload)."
                )
            )
            return

        # 3. Resolve fixture file path
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        candidate_paths = []
        if custom_fixture:
            candidate_paths.append(Path(custom_fixture))
        candidate_paths.extend([
            base_dir / "fixtures" / "seed_data.json",
            base_dir / "seed_data.json",
        ])

        target_file = None
        for p in candidate_paths:
            if p.exists() and p.is_file():
                target_file = p
                break

        if not target_file:
            self.stdout.write(
                self.style.ERROR(
                    f"Seed fixture file not found in candidates: {[str(p) for p in candidate_paths]}"
                )
            )
            return

        self.stdout.write(f"Loading complete seed data from '{target_file}'...")
        try:
            call_command("loaddata", str(target_file), verbosity=1)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully loaded seed data! Current database state: {Student.objects.count()} students, {School.objects.count()} schools."
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading seed fixture: {e}"))
            raise e
