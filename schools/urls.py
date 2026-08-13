from django.urls import path
from . import views

app_name = "schools"

urlpatterns = [
    # Portal View
    path("", views.portal_view, name="portal"),
    path("list/", views.school_list, name="school_list"),
    path("add/", views.school_create, name="school_create"),

    # REST APIs for Dashboard Features
    path("api/schools/", views.api_schools_list, name="api_schools_list"),
    path("api/schools/<int:school_id>/", views.api_school_detail, name="api_school_detail"),
    path("api/schools/create/", views.api_add_school, name="api_add_school"),
    path("api/schools/<int:school_id>/edit/", views.api_edit_school, name="api_edit_school"),
    path("api/schools/<int:school_id>/contact/", views.api_update_contact, name="api_update_contact"),
    path("api/schools/<int:school_id>/headmaster/", views.api_update_headmaster, name="api_update_headmaster"),
    path("api/schools/<int:school_id>/strength/", views.api_get_strength, name="api_get_strength"),
    path("api/schools/<int:school_id>/strength/update/", views.api_update_strength, name="api_update_strength"),
    path("api/schools/<int:school_id>/milestones/add/", views.api_add_milestone, name="api_add_milestone"),
    path("api/milestones/<int:milestone_id>/delete/", views.api_delete_milestone, name="api_delete_milestone"),
    path("api/schools/<int:school_id>/resources/add/", views.api_add_resource, name="api_add_resource"),
    path("api/resources/<int:resource_id>/delete/", views.api_delete_resource, name="api_delete_resource"),

    # CSV Export
    path("export/student-strength/", views.export_student_strength_csv, name="export_all_strength_csv"),
    path("export/student-strength/<int:school_id>/", views.export_student_strength_csv, name="export_strength_csv"),

    # Auth APIs
    path("api/auth/login/", views.api_login, name="api_login"),
    path("api/auth/logout/", views.api_logout, name="api_logout"),
]