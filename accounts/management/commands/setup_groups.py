"""
Management command to set up default groups and permissions for RBAC.
Run: python manage.py setup_groups
"""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Set up default groups and permissions for role-based access control"

    def handle(self, *args, **options):
        self.stdout.write("Setting up default groups and permissions...")

        # Define groups and their permissions
        groups_config = {
            "Academic Coordinator": {
                "description": "Manages student academic records and performance data",
                "permissions": [
                    "academics.view_academicrecord",
                    "academics.add_academicrecord",
                    "academics.change_academicrecord",
                    "students.view_student",
                    "schools.view_school",
                ],
            },
            "Warehouse Manager": {
                "description": "Manages inventory, stock, and laptop lifecycle",
                "permissions": [
                    "inventory.view_inventoryitem",
                    "inventory.add_inventoryitem",
                    "inventory.change_inventoryitem",
                    "inventory.view_stocktransaction",
                    "inventory.add_stocktransaction",
                    "inventory.view_laptop",
                    "inventory.add_laptop",
                    "inventory.change_laptop",
                    "inventory.view_laptopassignment",
                    "inventory.add_laptopassignment",
                    "inventory.change_laptopassignment",
                ],
            },
            "Distribution Manager": {
                "description": "Manages benefit distributions to students and schools",
                "permissions": [
                    "distributions.view_distribution",
                    "distributions.add_distribution",
                    "distributions.change_distribution",
                    "students.view_student",
                    "schools.view_school",
                    "eligibility.view_eligibilityrecord",
                ],
            },
            "Volunteer Coordinator": {
                "description": "Manages volunteers and event participation",
                "permissions": [
                    "volunteers.view_volunteer",
                    "volunteers.add_volunteer",
                    "volunteers.change_volunteer",
                    "volunteers.view_volunteeractivity",
                    "volunteers.add_volunteeractivity",
                    "volunteers.view_eventparticipation",
                    "volunteers.add_eventparticipation",
                    "events.view_event",
                    "events.add_event",
                    "events.change_event",
                ],
            },
            "Internship Coordinator": {
                "description": "Manages internship programs and placements",
                "permissions": [
                    "internships.view_internshipprogram",
                    "internships.add_internshipprogram",
                    "internships.change_internshipprogram",
                    "internships.view_internshipplacement",
                    "internships.add_internshipplacement",
                    "internships.change_internshipplacement",
                    "students.view_student",
                ],
            },
            "General Employee": {
                "description": "Basic read-only access to core modules",
                "permissions": [
                    "students.view_student",
                    "schools.view_school",
                    "eligibility.view_eligibilityrecord",
                ],
            },
        }

        created_count = 0
        updated_count = 0

        for group_name, config in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)

            if created:
                created_count += 1
                self.stdout.write(f"  Created group: {group_name}")
            else:
                updated_count += 1
                self.stdout.write(f"  Updated group: {group_name}")

            # Resolve and assign permissions
            valid_perms = []
            for perm_codename in config["permissions"]:
                try:
                    app_label, codename = perm_codename.split(".")
                    perm = Permission.objects.get(
                        codename=codename,
                        content_type__app_label=app_label,
                    )
                    valid_perms.append(perm)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"    Permission '{perm_codename}' not found, skipping."
                        )
                    )

            group.permissions.set(valid_perms)
            self.stdout.write(f"    Assigned {len(valid_perms)} permissions")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! Created {created_count} groups, updated {updated_count} groups."
            )
        )
