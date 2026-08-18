from django.shortcuts import render, redirect
from django.db.models import Sum
from .models import Distribution
from .forms import DistributionForm


def distribution_list(request):
    distributions = (
        Distribution.objects
        .select_related("student")
        .order_by("-distribution_date", "-created_at")
    )

    total_distributions = distributions.count()

    students_benefited = (
        distributions.values("student").distinct().count()
    )

    total_quantity = (
        distributions.aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )

    return render(
        request,
        "distributions/distribution_list.html",
        {
            "distributions": distributions,
            "total_distributions": total_distributions,
            "students_benefited": students_benefited,
            "total_quantity": total_quantity,
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
