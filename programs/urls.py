from django.urls import path
from . import views

app_name = "programs"

urlpatterns = [
    # Projects (Module 7)
    path("projects/", views.project_list, name="project_list"),
    path("projects/create/", views.project_create, name="project_create"),
    path("projects/<int:pk>/", views.project_detail, name="project_detail"),
    path("projects/<int:pk>/archive/", views.project_toggle_archive, name="project_toggle_archive"),

    # Programs with Mandatory Location (Module 11 & 16)
    path("programs/", views.program_list, name="program_list"),
    path("programs/create/", views.program_create, name="program_create"),
    path("programs/<int:pk>/", views.program_detail, name="program_detail"),
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

    # Scholarships: Foundation, Government, Employee Special (Module 8 & 9)
    path("scholarships/", views.scholarship_list, name="scholarship_list"),
    path("scholarships/create/", views.scholarship_create, name="scholarship_create"),
    path("scholarships/<int:pk>/update-status/", views.scholarship_update_status, name="scholarship_update_status"),
    path("scholarships/<int:pk>/archive/", views.scholarship_toggle_archive, name="scholarship_toggle_archive"),

    # Monthly Tracking (Module 6)
    path("monthly-tracking/", views.monthly_tracking, name="monthly_tracking"),

    # Archive Portal (Module 17)
    path("archive/", views.archive_portal, name="archive_portal"),
    path("archive/<str:model_type>/<int:pk>/restore/", views.archive_restore, name="archive_restore"),
]
