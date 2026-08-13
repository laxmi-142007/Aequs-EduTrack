from django.contrib import admin
from .models import Distribution, StudyKit, StudyKitItem


class StudyKitItemInline(admin.TabularInline):
    model = StudyKitItem
    extra = 2


@admin.register(StudyKit)
class StudyKitAdmin(admin.ModelAdmin):
    list_display = ("name", "target_grade_level", "is_active", "created_at")
    list_filter = ("is_active", "target_grade_level")
    search_fields = ("name", "description")
    inlines = [StudyKitItemInline]


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = (
        "benefit_type",
        "recipient_type",
        "student",
        "school",
        "inventory_item",
        "essential_item_type",
        "quantity",
        "academic_year",
        "distribution_date",
        "issued_by",
    )

    list_filter = (
        "benefit_type",
        "recipient_type",
        "essential_item_type",
        "academic_year",
        "distribution_date",
    )

    search_fields = (
        "student__student_name",
        "student__admission_number",
        "school__name",
        "school__udise_code",
        "inventory_item__item_name",
        "remarks",
    )

    readonly_fields = (
        "distribution_date",
        "created_at",
        "updated_at",
    )