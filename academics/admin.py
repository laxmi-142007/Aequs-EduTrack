from django.contrib import admin

from .forms import AcademicRecordForm
from .models import AcademicRecord


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):

    form = AcademicRecordForm

    list_display = (
        "student",
        "academic_year",
        "class_or_course",
        "marks_obtained",
        "total_marks",
        "percentage",
        "rank",
        "previous_class",
        "promotion_status",
    )

    list_filter = (
        "academic_year",
        "class_or_course",
        "promotion_status",
    )

    search_fields = (
        "student__student_name",
        "student__admission_number",
        "academic_year",
        "class_or_course",
    )

    ordering = (
        "-academic_year",
        "student__student_name",
    )

    readonly_fields = (
        "percentage",
        "rank",
        "previous_class",
    )