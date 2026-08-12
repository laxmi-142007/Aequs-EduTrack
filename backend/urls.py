from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Students
    path("students/", include("students.urls")),
]