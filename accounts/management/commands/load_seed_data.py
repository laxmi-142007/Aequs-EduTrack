from pathlib import Path
from django.core.management import call_command
from django.core.management.base import BaseCommand
from accounts.models import User
from schools.models import School
from students.models import Student
from programs.models import Program, Project
from trackers.models import WeeklyTrackerSession


class Command(BaseCommand):
    help = "Loads complete baseline seed data (students, schools, programs, scholarships, etc.) into the database if empty or forced."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reload fixture even if database already has students/schools/programs",
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

        # 1.5 Ensure baseline programs, projects, locations, and NGOs exist
        try:
            from programs.seeds import ensure_baseline_programs
            seeded_programs_count = ensure_baseline_programs()
            self.stdout.write(
                self.style.SUCCESS(f"Ensured {seeded_programs_count} baseline foundation programs & projects exist.")
            )
        except Exception as prog_err:
            self.stdout.write(self.style.WARNING(f"Note during baseline program seeding: {prog_err}"))

        # 2. Check if data is already fully populated
        student_count = Student.objects.count()
        school_count = School.objects.count()
        program_count = Program.objects.count()
        session_count = WeeklyTrackerSession.objects.count()

        is_fully_seeded = (
            program_count >= 30
            and student_count >= 9
            and school_count >= 500
            and session_count >= 500
        )

        if not force and is_fully_seeded:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Database already fully populated: {program_count} programs, {session_count} weekly sessions, {student_count} students, {school_count} schools present. Skipping seed fixture load (use --force to reload)."
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

        self.stdout.write(
            f"Loading complete seed data from '{target_file}' (current status: {program_count} programs, {session_count} sessions, {student_count} students, {school_count} schools)..."
        )
        try:
            call_command("loaddata", str(target_file), verbosity=1)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully loaded seed data via loaddata! Current database state: {Program.objects.count()} programs, {WeeklyTrackerSession.objects.count()} sessions, {Student.objects.count()} students, {School.objects.count()} schools."
                )
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Note on loaddata: {e}. Executing robust deserializer fallback..."))
            try:
                from django.db import connection, transaction
                # Reset connection in case previous loaddata left PostgreSQL transaction in aborted state
                if getattr(connection, "connection", None):
                    try:
                        connection.close()
                    except Exception:
                        pass

                from django.core.serializers import deserialize
                with open(target_file, "r", encoding="utf-8") as f:
                    objs = list(deserialize("json", f.read(), ignorenonexistent=True))
                saved_count = 0
                for item in objs:
                    try:
                        with transaction.atomic():
                            item.save()
                        saved_count += 1
                    except Exception:
                        pass
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Fallback deserializer completed: {saved_count} objects saved. Current programs: {Program.objects.count()}, schools: {School.objects.count()}."
                    )
                )
            except Exception as fb_err:
                self.stdout.write(self.style.ERROR(f"Fallback deserializer error: {fb_err}"))

        # Reset database sequences for PostgreSQL if running in production
        try:
            from django.core.management.color import no_style
            from django.db import connection
            from django.apps import apps

            if connection.vendor == "postgresql":
                commands = connection.ops.sequence_reset_sql(no_style(), apps.get_models())
                with connection.cursor() as cursor:
                    for sql in commands:
                        cursor.execute(sql)
                self.stdout.write(self.style.SUCCESS("PostgreSQL sequences successfully reset."))
        except Exception as seq_err:
            self.stdout.write(self.style.WARNING(f"Sequence reset note: {seq_err}"))
