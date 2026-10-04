from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Seeds or updates Super Admin user dhaval for user creation and portal governance."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username="dhaval",
            defaults={
                "email": "dhaval@aequs.com",
                "first_name": "Dhaval",
                "last_name": "Admin",
                "role": User.Role.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "must_change_password": False,
            }
        )
        user.set_password("AequsDhaval@2026!")
        user.role = User.Role.SUPER_ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} Super Admin user 'dhaval' (dhaval@aequs.com)."))
