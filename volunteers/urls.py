from django.urls import path
from . import views

app_name = "volunteers"

urlpatterns = [
    path("", views.volunteer_list, name="list"),
    path("add/", views.volunteer_create, name="create"),
    path("<int:pk>/", views.volunteer_detail, name="detail"),
    path("<int:pk>/edit/", views.volunteer_edit, name="edit"),
    path("<int:pk>/delete/", views.volunteer_delete, name="delete"),
    path("<int:pk>/activities/add/", views.activity_create, name="activity_create"),
    path("<int:pk>/events/add/", views.event_participation_create, name="event_participation_create"),
    path("export-csv/", views.volunteer_export_csv, name="export_csv"),
    path("export-excel/", views.volunteer_export_excel, name="export_excel"),
]