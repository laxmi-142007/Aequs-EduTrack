from django.urls import path

from . import views


app_name = "schools"


urlpatterns = [
    path("", views.school_list, name="list"),
    path("add/", views.school_create, name="create"),
]