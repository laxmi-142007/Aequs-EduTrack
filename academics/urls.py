from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    path("", views.academic_list, name="list"),
    path("add/", views.academic_create, name="create"),
    path("edit/<int:pk>/", views.academic_update, name="update"),
    path("delete/<int:pk>/", views.academic_delete, name="delete"),
]
