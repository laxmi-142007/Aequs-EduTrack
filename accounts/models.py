from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class SystemRole(models.Model):
    """
    Dynamic system role allowing administrators to configure custom roles,
    their administrative status, and associated functional permission groups.
    """
    name = models.CharField(max_length=60, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_admin = models.BooleanField(
        default=False,
        help_text="Designates whether users with this role have administrative portal privileges.",
    )
    group = models.OneToOneField(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_role",
        help_text="Underlying permission group automatically linked to this role.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "System Role"
        verbose_name_plural = "System Roles"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name.strip().upper().replace(" ", "_").replace("-", "_")
        super().save(*args, **kwargs)


class User(AbstractUser):

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "Admin"
        ACCOUNTANT = "ACCOUNTANT", "Accountant"
        VOLUNTEER = "VOLUNTEER", "Volunteer"
        EVENT_COORDINATOR = "EVENT_COORDINATOR", "Event Coordinator"

    role = models.CharField(
        max_length=50,
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

    # Track if user must change password on next login
    must_change_password = models.BooleanField(
        default=False,
        help_text="Force password change on next login",
    )

    @classmethod
    def get_all_role_choices(cls):
        """Returns built-in enum choices combined with any dynamic SystemRole entries."""
        choices = list(cls.Role.choices)
        existing_codes = {c[0] for c in choices}
        try:
            for sr in SystemRole.objects.all():
                if sr.code not in existing_codes:
                    choices.append((sr.code, sr.name))
                    existing_codes.add(sr.code)
        except Exception:
            pass
        return choices

    def get_role_display(self):
        """Returns the human-readable display label for built-in or custom roles."""
        for val, label in self.Role.choices:
            if self.role == val:
                return label
        try:
            sr = SystemRole.objects.filter(code=self.role).first()
            if sr:
                return sr.name
        except Exception:
            pass
        return self.role.replace("_", " ").title()

    def save(self, *args, **kwargs):
        # Auto-promote admin users to staff + superuser
        if self.role == self.Role.SUPER_ADMIN:
            self.is_staff = True
            self.is_superuser = True
        elif self.role == self.Role.ADMIN or self.is_admin:
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

    @property
    def is_admin(self):
        if self.role in (self.Role.ADMIN, self.Role.SUPER_ADMIN) or self.is_superuser:
            return True
        try:
            sr = SystemRole.objects.filter(code=self.role).first()
            if sr and sr.is_admin:
                return True
        except Exception:
            pass
        return False

    @property
    def is_employee(self):
        return not self.is_admin