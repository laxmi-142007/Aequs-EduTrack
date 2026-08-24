from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.report_list, name="list"),
    path("api/logs/", views.api_activity_logs, name="api_activity_logs"),
]
