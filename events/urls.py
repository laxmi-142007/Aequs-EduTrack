from django.urls import path

from . import views


app_name = "events"


urlpatterns = [

    # =========================================================================
    # EVENT LIST
    # =========================================================================

    path(
        "",
        views.event_list,
        name="list",
    ),

    # =========================================================================
    # NORMAL EVENT MANAGEMENT
    # =========================================================================

    path(
        "add/",
        views.event_create,
        name="create",
    ),

    path(
        "<int:pk>/edit/",
        views.event_edit,
        name="edit",
    ),

    path(
        "<int:pk>/delete/",
        views.event_delete,
        name="delete",
    ),

    # =========================================================================
    # PUBLIC EVENT FORM LINK
    # =========================================================================

    path(
        "form/create/",
        views.create_event_form_link,
        name="create_form_link",
    ),

    path(
        "form/share/<int:pk>/",
        views.share_event_form,
        name="share_form",
    ),

    # =========================================================================
    # QR CODE
    # =========================================================================

    path(
        "form/qr/<int:pk>/",
        views.event_form_qr,
        name="form_qr",
    ),

    # =========================================================================
    # EMPLOYEE PUBLIC FORM
    # =========================================================================

    path(
        "form/<str:token>/",
        views.public_event_form,
        name="public_form",
    ),

    # =========================================================================
    # SUCCESS PAGE
    # =========================================================================

    path(
        "success/<int:pk>/",
        views.event_success,
        name="success",
    ),
]
