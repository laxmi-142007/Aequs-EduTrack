from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "Admin"
        ACCOUNTANT = "ACCOUNTANT", "Accountant"
        VOLUNTEER = "VOLUNTEER", "Volunteer"
        EVENT_COORDINATOR = "EVENT_COORDINATOR", "Event Coordinator"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.VOLUNTEER,
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
    )

    profile_photo = models.ImageField(
        upload_to="users/",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"