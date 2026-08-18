from django.db import models


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

    class Meta:
        ordering = ["-event_date"]

    def __str__(self):
        return self.title
