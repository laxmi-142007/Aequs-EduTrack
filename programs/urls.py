from django.urls import path
from . import views

app_name = "programs"

urlpatterns = [
    # Projects (Module 7)
    path("projects/", views.project_list, name="project_list"),
    path("projects/create/", views.project_create, name="project_create"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),
    path("projects/<int:pk>/edit/", views.project_edit, name="project_edit"),
    path("projects/<int:pk>/link-program/", views.project_link_program, name="project_link_program"),
    path("projects/<int:pk>/unlink-program/<int:program_id>/", views.project_unlink_program, name="project_unlink_program"),
    path("projects/<int:pk>/archive/", views.project_toggle_archive, name="project_toggle_archive"),

    # Programs with Mandatory Location (Module 11 & 16)
    path("programs/", views.program_list, name="program_list"),
    path("programs/create/", views.program_create, name="program_create"),
    path("programs/<int:pk>/", views.program_detail, name="program_detail"),
    path("programs/<int:pk>/edit/", views.program_edit, name="program_edit"),
    path("programs/<int:pk>/link-project/", views.program_link_project, name="program_link_project"),
    path("programs/<int:pk>/archive/", views.program_toggle_archive, name="program_toggle_archive"),

    # Detailed EV Class Tracking (Module 4)
    path("ev-classes/", views.ev_class_list, name="ev_class_list"),
    path("ev-classes/create/", views.ev_class_create, name="ev_class_create"),
    path("ev-classes/<int:pk>/", views.ev_class_detail, name="ev_class_detail"),
    path("ev-classes/<int:pk>/archive/", views.ev_class_toggle_archive, name="ev_class_toggle_archive"),

    # NGO Management: Pratham, Agastya, Youth for Seva (Module 5)
    path("ngos/", views.ngo_list, name="ngo_list"),
    path("ngos/create/", views.ngo_create, name="ngo_create"),
    path("ngos/<int:pk>/", views.ngo_detail, name="ngo_detail"),
    path("ngos/<int:pk>/edit/", views.ngo_edit, name="ngo_edit"),
    path("ngos/<int:pk>/allocate-resource/", views.ngo_allocate_resource, name="ngo_allocate_resource"),

    # Scholarships: Foundation, Government, Employee Special (Module 8 & 9)
    path("scholarships/", views.scholarship_list, name="scholarship_list"),
    path("scholarships/create/", views.scholarship_create, name="scholarship_create"),
    path("scholarships/<int:pk>/update-status/", views.scholarship_update_status, name="scholarship_update_status"),
    path("scholarships/<int:pk>/archive/", views.scholarship_toggle_archive, name="scholarship_toggle_archive"),

    # Location Master (Module 16)
    path("locations/", views.location_list, name="location_list"),
    path("locations/create/", views.location_create, name="location_create"),
    path("locations/<int:pk>/edit/", views.location_edit, name="location_edit"),
    path("locations/<int:pk>/delete/", views.location_delete, name="location_delete"),

    # Mentorship Sessions
    path("mentorship/", views.mentorship_list, name="mentorship_list"),
    path("mentorship/create/", views.mentorship_create, name="mentorship_create"),
    path("mentorship/<int:pk>/edit/", views.mentorship_edit, name="mentorship_edit"),
    path("mentorship/<int:pk>/delete/", views.mentorship_delete, name="mentorship_delete"),

    # Monthly Tracking (Module 6)
    path("monthly-tracking/", views.monthly_tracking, name="monthly_tracking"),

    # Archive Portal (Module 17)
    path("archive/", views.archive_portal, name="archive_portal"),
    path("archive/<str:model_type>/<int:pk>/restore/", views.archive_restore, name="archive_restore"),
]

