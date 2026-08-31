from django.contrib import admin
from .models import School, SchoolMilestone, SchoolResource, GradeStrength


class SchoolMilestoneInline(admin.TabularInline):
    model = SchoolMilestone
    extra = 1


class SchoolResourceInline(admin.TabularInline):
    model = SchoolResource
    extra = 1


class GradeStrengthInline(admin.TabularInline):
    model = GradeStrength
    extra = 1


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "udise_code",
        "district",
        "taluk",
        "headmaster_name",
        "affiliation",
        "student_strength",
        "status",
    )

    list_filter = (
        "status",
        "district",
        "affiliation",
    )

    search_fields = (
        "name",
        "udise_code",
        "district",
        "headmaster_name",
    )

    inlines = [GradeStrengthInline, SchoolMilestoneInline, SchoolResourceInline]
    ordering = ("name",)


@admin.register(SchoolMilestone)
class SchoolMilestoneAdmin(admin.ModelAdmin):
    list_display = ("school", "title", "year_or_date", "created_at")
    list_filter = ("school",)
    search_fields = ("title", "details", "impact")


@admin.register(SchoolResource)
class SchoolResourceAdmin(admin.ModelAdmin):
    list_display = ("school", "resource_name", "status", "quantity", "last_updated_note")
    list_filter = ("status", "school")
    search_fields = ("resource_name", "details")


@admin.register(GradeStrength)
class GradeStrengthAdmin(admin.ModelAdmin):
    list_display = ("school", "grade_level", "student_names", "male_students", "female_students", "total_students", "change_vs_last_year")
    list_filter = ("school", "grade_level")