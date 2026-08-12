from django.shortcuts import render, redirect
from .models import Distribution
from .forms import DistributionForm


def distribution_list(request):
    distributions = (
        Distribution.objects
        .select_related("student")
        .order_by("-distribution_date")
    )

    return render(
        request,
        "distributions/distribution_list.html",
        {
            "distributions": distributions,
        },
    )


def distribution_create(request):
    if request.method == "POST":
        form = DistributionForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("distributions:list")
    else:
        form = DistributionForm()

    return render(
        request,
        "distributions/distribution_form.html",
        {
            "form": form,
        },
    )