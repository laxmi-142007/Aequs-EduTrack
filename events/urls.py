from django.urls import path

from . import views


app_name = "events"


urlpatterns = [

    path(
        "",
        views.event_list,
        name="list",
    ),

    path(
        "add/",
        views.event_create,
        name="create",
    ),

]
