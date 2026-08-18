from django.urls import path
from . import views

app_name = "distributions"

urlpatterns = [
    # Portal View
    path("", views.distribution_list, name="list"),
    path("add/", views.distribution_create, name="create"),
    path("add/", views.distribution_create, name="add"),

    # REST APIs - Eligibility & Student Pickers
    path("api/students/eligible/", views.api_eligible_students, name="api_eligible_students"),
    path("api/students/top-puc/", views.api_top_puc_students, name="api_top_puc_students"),
    path("api/study-kits/", views.api_study_kits, name="api_study_kits"),

    # REST APIs - Distributions
    path("api/distribute/book/", views.api_distribute_book, name="api_distribute_book"),
    path("api/distribute/workbook/", views.api_distribute_workbook, name="api_distribute_workbook"),
    path("api/distribute/study-kit/", views.api_issue_study_kit, name="api_issue_study_kit"),
    path("api/distribute/laptop/", views.api_issue_laptop_scholarship, name="api_issue_laptop"),
    path("api/distribute/school-essentials/", views.api_distribute_school_essentials, name="api_distribute_school_essentials"),

    # REST APIs - History & Reports
    path("api/history/", views.api_distribution_history, name="api_history"),
    path("api/reports/school-wise/", views.api_school_wise_report, name="api_school_wise_report"),
    path("api/reports/student-wise/", views.api_student_wise_report, name="api_student_wise_report"),
    path("api/export/csv/", views.api_export_distribution_csv, name="export_csv"),
]