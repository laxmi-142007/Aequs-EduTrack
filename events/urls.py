from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("add/", views.event_create, name="create"),
    path("<int:pk>/", views.event_detail, name="detail"),
    path("<int:pk>/edit/", views.event_edit, name="edit"),
    path("<int:pk>/delete/", views.event_delete, name="delete"),
    path("<int:pk>/assign-volunteer/", views.event_assign_volunteer, name="assign_volunteer"),
    path("<int:pk>/remove-volunteer/<int:participation_id>/", views.event_remove_volunteer, name="remove_volunteer"),
    path("<int:pk>/add-resource/", views.event_add_resource, name="add_resource"),
    path("<int:pk>/resources/<int:resource_id>/remove/", views.event_remove_resource, name="remove_resource"),
    path("<int:pk>/volunteer-signup/", views.event_volunteer_signup, name="volunteer_signup"),
    path("<int:pk>/volunteer-withdraw/", views.event_volunteer_withdraw, name="volunteer_withdraw"),
    path("<int:pk>/volunteers/<int:participation_id>/approve/", views.event_approve_volunteer, name="approve_volunteer"),
    path("<int:pk>/volunteers/<int:participation_id>/decline/", views.event_decline_volunteer, name="decline_volunteer"),
    path("export-csv/", views.event_export_csv, name="export_csv"),
    path("export-excel/", views.event_export_excel, name="export_excel"),
]
