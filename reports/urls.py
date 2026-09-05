from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # Reports & Audit Logs Dashboard
    path("", views.report_list, name="list"),
    path("api/logs/", views.api_activity_logs, name="api_activity_logs"),

    # Saved Reports Management & Exports
    path("create/", views.report_create, name="create"),
    path("<int:pk>/", views.report_detail, name="detail"),
    path("<int:pk>/edit/", views.report_edit, name="edit"),
    path("<int:pk>/delete/", views.report_delete, name="delete"),
    path("<int:pk>/export/csv/", views.report_export_csv, name="export_csv"),
    path("<int:pk>/export/excel/", views.report_export_excel, name="export_excel"),
]
