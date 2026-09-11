from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    # =========================================================================
    # EVENT DIRECTORY & MANAGEMENT
    # =========================================================================
    path("", views.event_list, name="list"),
    path("add/", views.event_create, name="create"),
    path("campaigns/create/", views.campaign_create, name="campaign_create"),
    path("campaigns/<int:pk>/edit/", views.campaign_edit, name="campaign_edit"),
    path("<int:pk>/", views.event_detail, name="detail"),
    path("<int:pk>/edit/", views.event_edit, name="edit"),
    path("<int:pk>/delete/", views.event_delete, name="delete"),

    # =========================================================================
    # PUBLIC EVENT FORM LINK & QR CODE
    # =========================================================================
    path("form/create/", views.create_event_form_link, name="create_form_link"),
    path("form/share/<int:pk>/", views.share_event_form, name="share_form"),
    path("form/qr/<int:pk>/", views.event_form_qr, name="form_qr"),
    path("form/<str:token>/", views.public_event_form, name="public_form"),
    path("success/<int:pk>/", views.event_success, name="success"),

    # =========================================================================
    # VOLUNTEER ASSIGNMENT & SIGN-UPS
    # =========================================================================
    path("<int:pk>/assign-volunteer/", views.event_assign_volunteer, name="assign_volunteer"),
    path("<int:pk>/remove-volunteer/<int:participation_id>/", views.event_remove_volunteer, name="remove_volunteer"),
    path("<int:pk>/volunteer-signup/", views.event_volunteer_signup, name="volunteer_signup"),
    path("<int:pk>/volunteer-withdraw/", views.event_volunteer_withdraw, name="volunteer_withdraw"),
    path("<int:pk>/volunteers/<int:participation_id>/approve/", views.event_approve_volunteer, name="approve_volunteer"),
    path("<int:pk>/volunteers/<int:participation_id>/decline/", views.event_decline_volunteer, name="decline_volunteer"),

    # =========================================================================
    # EVENT RESOURCES (INVENTORY ALLOCATION)
    # =========================================================================
    path("<int:pk>/add-resource/", views.event_add_resource, name="add_resource"),
    path("<int:pk>/resources/<int:resource_id>/remove/", views.event_remove_resource, name="remove_resource"),

    # =========================================================================
    # EVENT REMINDER (Module 10)
    # =========================================================================
    path("<int:pk>/send-reminder/", views.event_send_reminder, name="send_reminder"),
    path("send-due-reminders/", views.event_send_all_due_reminders, name="send_due_reminders"),

    # =========================================================================
    # EXPORTS
    # =========================================================================
    path("export-csv/", views.event_export_csv, name="export_csv"),
    path("export-excel/", views.event_export_excel, name="export_excel"),
]
