from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    LaptopForm,
    LaptopIssueForm,
    LaptopReplaceForm,
    LaptopReturnForm,
)
from .models import Laptop, LaptopAssignment
from .services import (
    issue_laptop,
    replace_laptop,
    return_laptop,
)


def inventory_list(request):
    laptops = Laptop.objects.all().order_by("asset_number")

    context = {
        "laptops": laptops,
        "total_laptops": laptops.count(),
        "available_laptops": laptops.filter(
            status=Laptop.Status.AVAILABLE
        ).count(),
        "issued_laptops": laptops.filter(
            status=Laptop.Status.ISSUED
        ).count(),
        "damaged_laptops": laptops.filter(
            status=Laptop.Status.DAMAGED
        ).count(),
    }

    return render(
        request,
        "inventory/inventory_list.html",
        context,
    )


def laptop_create(request):

    if request.method == "POST":
        form = LaptopForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Laptop added successfully.",
            )

            return redirect("inventory:list")

    else:
        form = LaptopForm()

    return render(
        request,
        "inventory/laptop_form.html",
        {
            "form": form,
            "title": "Add Laptop",
        },
    )


def laptop_issue(request):

    if request.method == "POST":
        form = LaptopIssueForm(request.POST)

        if form.is_valid():
            try:
                issue_laptop(
                    student=form.cleaned_data["student"],
                    laptop=form.cleaned_data["laptop"],
                    academic_year=form.cleaned_data["academic_year"],
                )

                messages.success(
                    request,
                    "Laptop issued successfully.",
                )

                return redirect("inventory:assignments")

            except ValidationError as exc:
                form.add_error(
                    None,
                    exc.message,
                )

    else:
        form = LaptopIssueForm()

    return render(
        request,
        "inventory/laptop_issue.html",
        {
            "form": form,
        },
    )


def laptop_return(request):

    if request.method == "POST":
        form = LaptopReturnForm(request.POST)

        if form.is_valid():
            try:
                return_laptop(
                    assignment=form.cleaned_data["assignment"],
                    return_notes=form.cleaned_data["return_notes"],
                )

                messages.success(
                    request,
                    "Laptop returned successfully.",
                )

                return redirect("inventory:assignments")

            except ValidationError as exc:
                form.add_error(
                    None,
                    exc.message,
                )

    else:
        form = LaptopReturnForm()

    return render(
        request,
        "inventory/laptop_return.html",
        {
            "form": form,
        },
    )


def laptop_replace(request):

    if request.method == "POST":
        form = LaptopReplaceForm(request.POST)

        if form.is_valid():
            try:
                replace_laptop(
                    assignment=form.cleaned_data["assignment"],
                    replacement_laptop=form.cleaned_data[
                        "replacement_laptop"
                    ],
                    reason=form.cleaned_data["reason"],
                )

                messages.success(
                    request,
                    "Laptop replaced successfully.",
                )

                return redirect("inventory:assignments")

            except ValidationError as exc:
                form.add_error(
                    None,
                    exc.message,
                )

    else:
        form = LaptopReplaceForm()

    return render(
        request,
        "inventory/laptop_replace.html",
        {
            "form": form,
        },
    )


def assignment_list(request):

    assignments = (
        LaptopAssignment.objects
        .select_related("student", "laptop")
        .order_by("-created_at")
    )

    return render(
        request,
        "inventory/assignment_list.html",
        {
            "assignments": assignments,
        },
    )
