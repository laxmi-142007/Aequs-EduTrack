from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    # Portal View
    path("", views.academic_portal, name="portal"),
    path("list/", views.academic_list, name="list"),

    # REST APIs
    path("api/records/", views.api_academic_records, name="api_records"),
    path("api/records/create/", views.api_create_academic_record, name="api_create"),
    path("api/records/<int:record_id>/update/", views.api_update_academic_record, name="api_update"),
    path("api/records/<int:record_id>/delete/", views.api_delete_academic_record, name="api_delete"),
    path("api/students/", views.api_get_students, name="api_students"),
    path("", views.academic_list, name="list"),
    path("add/", views.academic_create, name="create"),
    path("edit/<int:pk>/", views.academic_update, name="update"),
    path("delete/<int:pk>/", views.academic_delete, name="delete"),
]
