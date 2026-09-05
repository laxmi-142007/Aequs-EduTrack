# reports/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ActivityLog(models.Model):

    class ActionType(models.TextChoices):
        CREATE = "CREATE", "Created"
        UPDATE = "UPDATE", "Updated"
        DELETE = "DELETE", "Deleted"
        LOGIN = "LOGIN", "Logged In"
        LOGOUT = "LOGOUT", "Logged Out"
        VIEW = "VIEW", "Viewed"
        EXPORT = "EXPORT", "Exported"
        IMPORT = "IMPORT", "Imported"
        OTHER = "OTHER", "Other"

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )

    action = models.CharField(
        max_length=255
    )

    action_type = models.CharField(
        max_length=30,
        choices=ActionType.choices,
        default=ActionType.OTHER,
    )

    category = models.CharField(
        max_length=50,
        default="GENERAL",
        db_index=True,
    )

    object_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    object_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    details = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return (
            f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] "
            f"{self.action}"
        )


def log_activity(
    user_or_request,
    action,
    category="GENERAL",
    details="",
    action_type=ActivityLog.ActionType.OTHER,
    object_type="",
    object_id=None,
):
    """
    Central function used by the application to create audit logs.
    """

    user = None

    if hasattr(user_or_request, "user"):
        request_user = user_or_request.user

        if request_user.is_authenticated:
            user = request_user

    elif isinstance(user_or_request, User):
        user = user_or_request

    return ActivityLog.objects.create(
        user=user,
        action=str(action)[:255],
        action_type=action_type,
        category=str(category).upper(),
        object_type=object_type or "",
        object_id=str(object_id) if object_id is not None else None,
        details=details or "",
    )
