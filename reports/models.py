from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    category = models.CharField(max_length=50, default="GENERAL")
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.action}"


def log_activity(user_or_request, action, category="GENERAL", details=""):
    user = None
    if hasattr(user_or_request, "user"):
        user = user_or_request.user if user_or_request.user.is_authenticated else None
    elif isinstance(user_or_request, User):
        user = user_or_request
    
    return ActivityLog.objects.create(
        user=user,
        action=action,
        category=category.upper(),
        details=details
    )
