from django.urls import path
from . import views

app_name = "trackers"

urlpatterns = [
    # Default routes (defaults to Youth for Seva)
    path("", views.session_list_view, {"ngo_slug": "yfs"}, name="session_list"),
    path("upload/", views.upload_tracker_view, {"ngo_slug": "yfs"}, name="upload_tracker"),
    path("enrollments/", views.enrollment_list_view, {"ngo_slug": "yfs"}, name="enrollment_list"),
    path("export/csv/", views.export_sessions_csv, {"ngo_slug": "yfs"}, name="export_csv"),

    # NGO-specific routes (yfs, agastya, pratham)
    path("<str:ngo_slug>/", views.session_list_view, name="ngo_session_list"),
    path("<str:ngo_slug>/upload/", views.upload_tracker_view, name="ngo_upload_tracker"),
    path("<str:ngo_slug>/upload/", views.upload_tracker_view, name="ngo_upload_workbook"),
    path("<str:ngo_slug>/enrollments/", views.enrollment_list_view, name="ngo_enrollment_list"),
    path("<str:ngo_slug>/export/csv/", views.export_sessions_csv, name="ngo_export_csv"),
]
