import os
from django.core.management.base import BaseCommand
from django.conf import settings
from programs.models import Program, NGO
from programs.roster import parse_and_save_roster


class Command(BaseCommand):
    help = "Seed Agastya International Foundation School Profile by parsing the sample Excel roster"

    def handle(self, *args, **options):
        self.stdout.write("Parsing Agastya School Profile from Excel...")

        ngo, _ = NGO.objects.get_or_create(
            code="AGASTYA",
            defaults={"name": "Agastya International Foundation"}
        )

        program = Program.objects.filter(pk=18).first()
        if not program:
            program = Program.objects.filter(code__icontains="MSL").first()
        if not program:
            program = Program.objects.filter(title__icontains="Mobile Science Lab").first()

        excel_path = os.path.join(settings.BASE_DIR, "backend", "static", "test_agastya_roster.xlsx")
        if not os.path.exists(excel_path):
            self.stderr.write(f"Sample file not found at {excel_path}")
            return

        if program:
            program.ngo = ngo
            program.save(update_fields=["ngo"])
            with open(excel_path, "rb") as f:
                res = parse_and_save_roster(program, f)
            self.stdout.write(self.style.SUCCESS(
                f"Successfully parsed Excel and linked {len(res['schools'])} schools to Program {program.pk} ({program.title})"
            ))
        else:
            self.stdout.write("No matching program found to attach roster to.")
