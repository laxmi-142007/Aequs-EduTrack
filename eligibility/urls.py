from django.urls import path
from . import views

app_name = "eligibility"

urlpatterns = [
    # Main Portal Page
    path("", views.eligibility_portal, name="portal"),

    # REST APIs
    path("api/records/", views.api_eligibility_records, name="api_records"),
    path("api/summary/", views.api_eligibility_summary, name="api_summary"),
    path("api/run-evaluation/", views.api_run_evaluation, name="api_run_evaluation"),
    path("api/create/", views.api_create_eligibility_record, name="api_create"),
    path("api/update/<int:record_id>/", views.api_update_eligibility_record, name="api_update"),
    path("api/toggle/<int:record_id>/", views.api_toggle_eligibility, name="api_toggle"),
    path("api/delete/<int:record_id>/", views.api_delete_eligibility_record, name="api_delete"),
    path("api/student-profile/<int:student_id>/", views.api_student_profile, name="api_student_profile"),

    # Export
    path("export/csv/", views.export_eligibility_csv, name="export_csv"),
]
