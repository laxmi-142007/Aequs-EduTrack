from django.urls import path
from . import views

app_name = "eligibility"

urlpatterns = [
    path("", views.eligibility_list, name="list"),
]
