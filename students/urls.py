from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("", views.student_list, name="list"),
    path("add/", views.add_student, name="add"),
    path("bulk-upload/", views.bulk_upload_students, name="bulk_upload"),
    path("clear/", views.clear_all_students, name="clear_all"),
    path("<int:pk>/", views.student_detail, name="detail"),
]
