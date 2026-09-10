from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("", views.student_list, name="list"),
    path("add/", views.add_student, name="add"),
    path("bulk-upload/", views.bulk_upload_students, name="bulk_upload"),
    path("clear/", views.clear_all_students, name="clear_all"),
    path("id-cards/", views.bulk_id_cards, name="bulk_id_cards"),
    path("<int:pk>/", views.student_detail, name="detail"),
    path("<int:pk>/edit/", views.edit_student, name="edit"),
    path("<int:pk>/id-card/", views.student_id_card, name="id_card"),
    path("<int:pk>/qr/", views.student_qr_code, name="qr_code"),
]

