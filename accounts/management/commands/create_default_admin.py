from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Ensures the default Super Admin user exists in the configured database (MSSQL or SQLite)."

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, default="admin", help="Admin username (default: admin)")
        parser.add_argument("--password", type=str, default="admin123", help="Admin password (default: admin123)")
        parser.add_argument("--email", type=str, default="admin@aequsedutrack.org", help="Admin email")

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        email = options["email"]

        user = User.objects.filter(username__iexact=username).first()
        if not user:
            user = User(
                username=username,
                email=email,
            )
            created = True
        else:
            created = False

        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.role = "SUPER_ADMIN"
        user.must_change_password = False
        user.save()

        action = "Created" if created else "Updated & reset password for"
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully {action} Super Admin user: '{user.username}' (password: '{password}')"
            )
        )
