from django.contrib import admin
from .models import Report, ActivityLog


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "report_type", "status", "row_limit", "visibility", "has_attachment", "created_by", "created_at")
    list_filter = ("report_type", "status", "visibility", "created_at")
    search_fields = ("title", "description", "summary_notes", "allowed_roles")
    filter_horizontal = ("allowed_groups",)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "category", "action", "user")
    list_filter = ("category", "timestamp")
    search_fields = ("action", "details", "user__username")
