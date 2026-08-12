from django.contrib import admin

from .models import Laptop, LaptopAssignment


@admin.register(Laptop)
class LaptopAdmin(admin.ModelAdmin):

    list_display = (
        "asset_number",
        "serial_number",
        "brand",
        "model_name",
        "condition",
        "status",
        "purchase_date",
    )

    list_filter = (
        "status",
        "condition",
        "brand",
    )

    search_fields = (
        "asset_number",
        "serial_number",
        "brand",
        "model_name",
    )


@admin.register(LaptopAssignment)
class LaptopAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "laptop",
        "academic_year",
        "status",
        "issued_date",
        "returned_date",
    )

    list_filter = (
        "status",
        "academic_year",
    )

    search_fields = (
        "student__student_name",
        "laptop__asset_number",
        "laptop__serial_number",
    )