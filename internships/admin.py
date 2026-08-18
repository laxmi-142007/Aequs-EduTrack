from django.contrib import admin
from .models import InternshipProgram, InternshipPlacement, InternshipMilestone


class InternshipMilestoneInline(admin.TabularInline):
    model = InternshipMilestone
    extra = 1


@admin.register(InternshipProgram)
class InternshipProgramAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "program_code",
        "department",
        "company_name",
        "duration_months",
        "stipend_amount",
        "total_slots",
        "academic_year",
        "status",
        "created_at",
    )
    list_filter = ("status", "department", "academic_year", "company_name")
    search_fields = ("title", "program_code", "company_name", "mentor_in_charge")


@admin.register(InternshipPlacement)
class InternshipPlacementAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "program",
        "department",
        "company_name",
        "academic_year",
        "status",
        "performance_grade",
        "stipend_amount",
        "certificate_issued",
        "start_date",
    )
    list_filter = (
        "status",
        "department",
        "performance_grade",
        "certificate_issued",
        "academic_year",
    )
    search_fields = (
        "student__student_name",
        "student__admission_number",
        "project_title",
        "mentor_name",
        "certificate_number",
    )
    inlines = [InternshipMilestoneInline]


@admin.register(InternshipMilestone)
class InternshipMilestoneAdmin(admin.ModelAdmin):
    list_display = ("placement", "title", "due_date", "status", "completed_date")
    list_filter = ("status", "due_date")
    search_fields = ("placement__student__student_name", "title")
