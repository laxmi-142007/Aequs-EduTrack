from django.contrib import admin
from schools.models import School
from trackers.models import SchoolEnrollment, WeeklyTrackerSession


@admin.register(SchoolEnrollment)
class SchoolEnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "academic_year",
        "programme",
        "standard",
        "boys",
        "girls",
        "total",
    )
    list_filter = (
        "academic_year",
        "programme",
        "standard",
    )
    search_fields = (
        "school__name",
        "standard",
    )
    ordering = ("academic_year", "programme", "school__name", "standard")


@admin.register(WeeklyTrackerSession)
class WeeklyTrackerSessionAdmin(admin.ModelAdmin):
    list_display = (
        "session_date",
        "academic_year",
        "programme",
        "school",
        "standard",
        "instructor_name",
        "session_type",
        "total_exposures",
        "teacher_present",
    )
    list_filter = (
        "academic_year",
        "programme",
        "session_type",
        "teacher_present",
        "standard",
    )
    search_fields = (
        "school__name",
        "raw_location_or_activity",
        "instructor_name",
        "topic",
    )
    date_hierarchy = "session_date"
    ordering = ("-session_date", "-id")


# Ensure School registration supports code_aliases
try:
    if not admin.site.is_registered(School):
        @admin.register(School)
        class SchoolAdmin(admin.ModelAdmin):
            list_display = ("name", "udise_code", "district", "code_aliases")
            search_fields = ("name", "udise_code")
except Exception:
    pass
