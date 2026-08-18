from django.urls import path
from . import views

app_name = "internships"

urlpatterns = [
    # Main Portal View
    path("", views.internship_portal, name="portal"),
    path("list/", views.internship_portal, name="list"),

    # REST APIs - Placements & Interns
    path("api/internships/", views.api_internships, name="api_internships"),
    path("api/internships/create/", views.api_create_internship, name="api_create_internship"),
    path("api/internships/<int:placement_id>/update/", views.api_update_internship, name="api_update_internship"),
    path("api/internships/<int:placement_id>/status/", views.api_update_status, name="api_update_status"),
    path("api/internships/<int:placement_id>/delete/", views.api_delete_internship, name="api_delete_internship"),

    # REST APIs - Programs & Openings
    path("api/programs/", views.api_programs, name="api_programs"),
    path("api/programs/create/", views.api_create_program, name="api_create_program"),
    path("api/programs/<int:program_id>/update/", views.api_update_program, name="api_update_program"),
    path("api/programs/<int:program_id>/delete/", views.api_delete_program, name="api_delete_program"),

    # Candidate Pool & 1-Click Allocation
    path("api/candidates/", views.api_eligible_candidates, name="api_candidates"),
    path("api/quick-assign/", views.api_quick_assign_candidate, name="api_quick_assign"),

    # Analytics Summary & CSV Export
    path("api/summary/", views.api_summary, name="api_summary"),
    path("export/csv/", views.api_export_csv, name="export_csv"),
    path("", views.internship_list, name="list"),
]
