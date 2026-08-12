from django.contrib import admin
from .models import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "udise_code",
        "district",
        "taluk",
        "headmaster_name",
        "student_strength",
        "status",
    )

    list_filter = (
        "status",
        "district",
    )

    search_fields = (
        "name",
        "udise_code",
        "district",
        "headmaster_name",
    )

    ordering = ("name",)