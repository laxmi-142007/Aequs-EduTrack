from django.shortcuts import render, redirect
from .models import School
from .forms import SchoolForm


def school_list(request):
    schools = School.objects.all().order_by("name")

    return render(
        request,
        "schools/list.html",
        {
            "schools": schools,
        },
    )


def school_create(request):
    if request.method == "POST":
        form = SchoolForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("school_list")
    else:
        form = SchoolForm()

    return render(
        request,
        "schools/form.html",
        {
            "form": form,
        },
    )