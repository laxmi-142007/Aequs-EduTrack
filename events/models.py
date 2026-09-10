from django.db import models
import secrets


class EventFormLink(models.Model):

    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def save(self, *args, **kwargs):

        if not self.token:
            self.token = secrets.token_urlsafe(32)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Event Form - {self.token}"


class Event(models.Model):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned / Upcoming"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    title = models.CharField(
        max_length=200
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        blank=True,
    )

    description = models.TextField(
        blank=True
    )

    event_date = models.DateField()

    location = models.CharField(
        max_length=200,
        blank=True
    )

    organizer = models.CharField(
        max_length=150,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    requested_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_requests",
    )

    requested_quantity = models.PositiveIntegerField(
        default=0,
    )

    # Event Reminder feature (Module 10)
    reminder_sent = models.BooleanField(
        default=False,
        help_text="Automated reminder sent to organizers and volunteers",
    )
    reminder_scheduled_date = models.DateField(
        null=True,
        blank=True,
        help_text="Configured notification trigger date",
    )

    class Meta:
        ordering = ["-event_date"]

    def __str__(self):
        return self.title

    @property
    def is_past(self):
        from django.utils import timezone
        return self.event_date < timezone.now().date()

    @property
    def volunteer_count(self):
        return self.volunteer_participations.count()

    @property
    def total_volunteer_hours(self):
        from django.db.models import Sum
        total = self.volunteer_participations.aggregate(Sum("hours_contributed"))["hours_contributed__sum"]
        return total or 0

    @property
    def total_resource_count(self):
        return self.resources.count()

    @property
    def total_resource_units(self):
        from django.db.models import Sum
        units = self.resources.aggregate(Sum("quantity"))["quantity__sum"]
        return units if units is not None else (self.requested_quantity or 0)


class EventResource(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="resources",
    )
    item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.CASCADE,
        related_name="event_allocations",
    )
    quantity = models.PositiveIntegerField(
        default=1,
    )
    allocated_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-allocated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "item"],
                name="unique_event_resource",
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.item.item_name} for {self.event.title}"
