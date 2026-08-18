from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", views.dashboard, name="dashboard"),

    path("students/", include("students.urls")),
    path("schools/", include("schools.urls")),
    path("distributions/", include("distributions.urls")),
    path("academics/", include("academics.urls")),
    path("eligibility/", include("eligibility.urls")),
    path("inventory/", include("inventory.urls")),
    path("internships/", include("internships.urls")),
    path("reports/", include("reports.urls")),
    path("events/", include("events.urls")),
    path("volunteers/", include("volunteers.urls")),
]
