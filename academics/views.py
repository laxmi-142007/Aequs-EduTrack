from django.shortcuts import render, redirect, get_object_or_404

from .models import AcademicRecord
from .forms import AcademicRecordForm


def academic_list(request):
    records = AcademicRecord.objects.select_related("student").all()

    return render(
        request,
        "academics/academic_list.html",
        {
            "records": records,
        },
    )


def academic_create(request):
    if request.method == "POST":
        form = AcademicRecordForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("academics:list")
    else:
        form = AcademicRecordForm()

    return render(
        request,
        "academics/academic_form.html",
        {
            "form": form,
        },
    )


def academic_update(request, pk):
    record = get_object_or_404(AcademicRecord, pk=pk)

    if request.method == "POST":
        form = AcademicRecordForm(request.POST, instance=record)

        if form.is_valid():
            form.save()
            return redirect("academics:list")
    else:
        form = AcademicRecordForm(instance=record)

    return render(
        request,
        "academics/academic_form.html",
        {
            "form": form,
            "record": record,
        },
    )


def academic_delete(request, pk):
    record = get_object_or_404(AcademicRecord, pk=pk)

    if request.method == "POST":
        record.delete()
        return redirect("academics:list")

    return render(
        request,
        "academics/academic_confirm_delete.html",
        {
            "record": record,
        },
    )