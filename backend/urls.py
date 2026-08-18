from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", views.dashboard, name="dashboard"),

    # Schools - Government School Management Portal & APIs
    path("schools/", include("schools.urls")),

    # Students
    path("students/", include("students.urls")),

    # Academics
    path("academics/", include("academics.urls")),

    # Distributions
    path("distributions/", include("distributions.urls")),

    # Inventory - Inventory Management Portal & APIs
    path("inventory/", include("inventory.urls")),

    # Eligibility - Student Benefit Eligibility Portal & APIs
    path("eligibility/", include("eligibility.urls")),

    # Internships - Aequs Corporate & Industrial Internship Portal
    path("internships/", include("internships.urls")),

    # Reports
    path("reports/", include("reports.urls")),

    # Events
    path("events/", include("events.urls")),

    # Volunteers
    path("volunteers/", include("volunteers.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
