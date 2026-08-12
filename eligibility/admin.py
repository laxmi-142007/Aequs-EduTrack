from django.contrib import admin
from .models import EligibilityRecord


@admin.register(EligibilityRecord)
class EligibilityRecordAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "benefit_type",
        "academic_year",
        "eligible",
        "selection_rank",
        "checked_at",
    )

    list_filter = (
        "benefit_type",
        "eligible",
        "academic_year",
    )

    search_fields = (
        "student__student_name",
        "student__admission_number",
    )

    ordering = (
        "-academic_year",
        "benefit_type",
        "selection_rank",
    )