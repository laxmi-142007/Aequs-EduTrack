from django.urls import path
from .views import school_list, school_create

urlpatterns = [
    path("", school_list, name="school_list"),
    path("add/", school_create, name="school_create"),
]