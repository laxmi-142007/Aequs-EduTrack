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

    title = models.CharField(
        max_length=200
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

    class Meta:
        ordering = ["-event_date"]

    def __str__(self):
        return self.title
