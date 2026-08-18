from django.shortcuts import render, redirect

from .models import School
from .forms import SchoolForm


def school_list(request):
    schools = School.objects.all().order_by("name")

    return render(
        request,
        "schools/school_list.html",
        {
            "schools": schools,
        },
    )


def school_create(request):

    if request.method == "POST":
        form = SchoolForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("schools:list")

    else:
        form = SchoolForm()

    return render(
        request,
        "schools/school_form.html",
        {
            "form": form,
        },
    )