from django.contrib import admin
from .models import (
    InventoryItem,
    StockTransaction,
    Laptop,
    LaptopAssignment,
)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_name",
        "sku",
        "category",
        "current_stock",
        "unit",
        "low_stock_threshold",
        "unit_cost",
        "location",
        "status",
    )
    list_filter = (
        "category",
        "status",
    )
    search_fields = (
        "item_name",
        "sku",
        "location",
        "description",
    )


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_date",
        "item",
        "transaction_type",
        "quantity",
        "previous_stock",
        "new_stock",
        "source_destination",
        "reference_number",
        "performed_by",
    )
    list_filter = (
        "transaction_type",
        "transaction_date",
        "item__category",
    )
    search_fields = (
        "item__item_name",
        "item__sku",
        "source_destination",
        "reference_number",
        "performed_by",
    )


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