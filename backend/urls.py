from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", RedirectView.as_view(pattern_name="accounts:dashboard_redirect", permanent=False), name="dashboard"),

    # Portal routes (RBAC-protected dashboards & user management)
    path("", include("accounts.urls")),

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
