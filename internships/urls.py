from django.urls import path
from . import views

app_name = "internships"

urlpatterns = [

    # ============================================================
    # MAIN INTERNSHIP PORTAL
    # ============================================================

    path(
        "",
        views.internship_portal,
        name="portal",
    ),

    path(
        "list/",
        views.internship_portal,
        name="list",
    ),


    # ============================================================
    # INTERNSHIP DOCUMENTS
    # ============================================================

    path(
        "documents/<int:placement_id>/",
        views.internship_documents,
        name="documents",
    ),

    path(
        "documents/upload/",
        views.internship_documents,
        name="upload_internship_document",

    ),

    path(
        "documents/<int:document_id>/download/",
        views.download_internship_document,
        name="download_document",
    ),

    path(
        "documents/<int:document_id>/delete/",
        views.delete_internship_document,
        name="delete_document",
    ),


    # ============================================================
    # REST APIs - PLACEMENTS & INTERNS
    # ============================================================

    path(
        "api/internships/",
        views.api_internships,
        name="api_internships",
    ),

    path(
        "api/internships/create/",
        views.api_create_internship,
        name="api_create_internship",
    ),

    path(
        "api/internships/<int:placement_id>/update/",
        views.api_update_internship,
        name="api_update_internship",
    ),

    path(
        "api/internships/<int:placement_id>/status/",
        views.api_update_status,
        name="api_update_status",
    ),

    path(
        "api/internships/<int:placement_id>/delete/",
        views.api_delete_internship,
        name="api_delete_internship",
    ),


    # ============================================================
    # REST APIs - PROGRAMS & OPENINGS
    # ============================================================

    path(
        "api/programs/",
        views.api_programs,
        name="api_programs",
    ),

    path(
        "api/programs/create/",
        views.api_create_program,
        name="api_create_program",
    ),

    path(
        "api/programs/<int:program_id>/update/",
        views.api_update_program,
        name="api_update_program",
    ),

    path(
        "api/programs/<int:program_id>/delete/",
        views.api_delete_program,
        name="api_delete_program",
    ),


    # ============================================================
    # CANDIDATE POOL & QUICK ASSIGN
    # ============================================================

    path(
        "api/candidates/",
        views.api_eligible_candidates,
        name="api_candidates",
    ),

    path(
        "api/quick-assign/",
        views.api_quick_assign_candidate,
        name="api_quick_assign",
    ),


    # ============================================================
    # ANALYTICS & EXPORT
    # ============================================================

    path(
        "api/summary/",
        views.api_summary,
        name="api_summary",
    ),

    path(
        "export/csv/",
        views.api_export_csv,
        name="export_csv",
    ),
]
