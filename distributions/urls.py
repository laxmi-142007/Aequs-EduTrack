from django.urls import path
from . import views

app_name = "distributions"

urlpatterns = [
    path("", views.distribution_list, name="list"),
    path("add/", views.distribution_create, name="create"),
]