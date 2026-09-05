from django.urls import path
from . import views

app_name = "volunteers"

urlpatterns = [
    path("", views.volunteer_list, name="list"),
    path("add/", views.volunteer_create, name="create"),
    path("registration/", views.public_volunteer_registration, name="registration"),
    path("register/", views.public_volunteer_registration, name="register"),
    path("<int:pk>/", views.volunteer_detail, name="detail"),
    path("<int:pk>/edit/", views.volunteer_edit, name="edit"),
    path("<int:pk>/delete/", views.volunteer_delete, name="delete"),
    path("<int:pk>/activities/add/", views.activity_create, name="activity_create"),
    path("<int:pk>/events/add/", views.event_participation_create, name="event_participation_create"),
    path("export-csv/", views.volunteer_export_csv, name="export_csv"),
    path("export-excel/", views.volunteer_export_excel, name="export_excel"),
    # Public volunteer registration form link & QR
    path("form/generate-json/", views.generate_volunteer_form_link_json, name="generate_form_link_json"),
    path("form/create/", views.create_volunteer_form_link, name="create_form_link"),
    path("form/share/<int:pk>/", views.share_volunteer_form, name="share_form"),
    path("form/qr/<str:token>/", views.volunteer_form_qr_by_token, name="form_qr_by_token"),
    path("form/qr/<int:pk>/", views.volunteer_form_qr, name="form_qr"),
    path("form/<str:token>/", views.public_volunteer_registration, name="public_form_by_token"),
    path("register/public/", views.public_volunteer_registration, name="public_registration"),
    path("form/public/", views.public_volunteer_registration, name="public_form"),
    path("registration/success/", views.volunteer_registration_success, name="registration_success"),
    path("registration/qr/", views.volunteer_registration_qr, name="registration_qr"),
]