from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    # Portal View
    path("", views.inventory_portal, name="portal"),

    # REST APIs - Inventory Items
    path("api/items/", views.api_inventory_items, name="api_items"),
    path("api/items/create/", views.api_create_inventory_item, name="api_create_item"),
    path("api/items/<int:item_id>/update/", views.api_update_inventory_item, name="api_update_item"),
    path("api/items/<int:item_id>/delete/", views.api_delete_inventory_item, name="api_delete_item"),

    # REST APIs - Stock Movements
    path("api/stock/in/", views.api_stock_in, name="api_stock_in"),
    path("api/stock/out/", views.api_stock_out, name="api_stock_out"),
    path("api/transactions/", views.api_stock_transactions, name="api_transactions"),
    path("api/alerts/low-stock/", views.api_low_stock_alerts, name="api_low_stock_alerts"),

    # REST APIs - Laptops
    path("api/laptops/", views.api_laptops, name="api_laptops"),
    path("api/laptops/create/", views.api_create_laptop, name="api_create_laptop"),
    path("api/laptops/issue/", views.api_issue_laptop, name="api_issue_laptop"),
    path("api/laptops/<int:laptop_id>/return/", views.api_return_laptop, name="api_return_laptop"),

    # CSV Export
    path("export/csv/", views.api_export_csv, name="export_csv"),
]
