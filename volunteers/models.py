from django.db import models
from events.models import Event


class Volunteer(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    ]

    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("OTHER", "Other"),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)

    occupation = models.CharField(max_length=150, blank=True)
    qualification = models.CharField(max_length=150, blank=True)

    skills = models.TextField(
        blank=True,
        help_text="Enter skills separated by commas"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    registration_date = models.DateField(auto_now_add=True)
    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class VolunteerActivity(models.Model):
    STATUS_CHOICES = [
        ("ASSIGNED", "Assigned"),
        ("ONGOING", "Ongoing"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    volunteer = models.ForeignKey(
        Volunteer,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    activity_name = models.CharField(max_length=200)
    activity_date = models.DateField()
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ASSIGNED"
    )

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-activity_date"]

    def __str__(self):
        return f"{self.volunteer} - {self.activity_name}"


class EventParticipation(models.Model):
    STATUS_CHOICES = [
        ("ASSIGNED", "Assigned"),
        ("ATTENDED", "Attended"),
        ("ABSENT", "Absent"),
        ("CANCELLED", "Cancelled"),
    ]

    volunteer = models.ForeignKey(
        Volunteer,
        on_delete=models.CASCADE,
        related_name="event_participations"
    )

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="volunteer_participations"
    )

    role = models.CharField(
        max_length=150,
        blank=True
    )

    participation_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ASSIGNED"
    )

    hours_contributed = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    remarks = models.TextField(blank=True)

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assigned_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["volunteer", "event"],
                name="unique_volunteer_event"
            )
        ]

    def __str__(self):
        return f"{self.volunteer} - {self.event}"
