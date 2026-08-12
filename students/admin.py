from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    list_display = (
        "admission_number",
        "student_name",
        "school",
        "current_class",
        "section",
        "gender",
        "parent_name",
        "status",
    )

    list_filter = (
        "school",
        "current_class",
        "gender",
        "status",
    )

    search_fields = (
        "admission_number",
        "student_name",
        "parent_name",
        "parent_phone",
    )

    ordering = (
        "student_name",
    )