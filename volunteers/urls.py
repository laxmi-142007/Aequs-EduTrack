from django.urls import path

from . import views


app_name = "volunteers"


urlpatterns = [

    # Volunteer list
    path(
        "",
        views.volunteer_list,
        name="list",
    ),

    # Add new volunteer
    path(
        "add/",
        views.volunteer_create,
        name="create",
    ),

    # Volunteer details
    path(
        "<int:pk>/",
        views.volunteer_detail,
        name="detail",
    ),

    # Add activity for a volunteer
    path(
        "<int:pk>/activities/add/",
        views.activity_create,
        name="activity_create",
    ),

    # Add event participation for a volunteer
    path(
        "<int:pk>/events/add/",
        views.event_participation_create,
        name="event_participation_create",
    ),

]