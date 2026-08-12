from django.contrib import admin
from .models import Distribution


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "benefit_type",
        "academic_year",
        "quantity",
        "distribution_date",
        "issued_by",
    )

    list_filter = (
        "benefit_type",
        "academic_year",
        "distribution_date",
    )

    search_fields = (
        "student__student_name",
        "student__admission_number",
    )

    readonly_fields = (
        "distribution_date",
        "created_at",
        "updated_at",
    )