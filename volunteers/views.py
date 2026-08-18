from django.shortcuts import render, redirect, get_object_or_404

from .models import (
    Volunteer,
    VolunteerActivity,
    EventParticipation,
)

from events.models import Event


def volunteer_list(request):

    volunteers = Volunteer.objects.all()

    return render(
        request,
        "volunteers/volunteer_list.html",
        {
            "volunteers": volunteers,
        },
    )


def volunteer_create(request):

    if request.method == "POST":

        Volunteer.objects.create(
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
            email=request.POST.get("email"),
            phone=request.POST.get("phone"),
            gender=request.POST.get("gender"),
            date_of_birth=request.POST.get("date_of_birth") or None,
            address=request.POST.get("address"),
            city=request.POST.get("city"),
            state=request.POST.get("state"),
            pincode=request.POST.get("pincode"),
            occupation=request.POST.get("occupation"),
            qualification=request.POST.get("qualification"),
            skills=request.POST.get("skills"),
            status=request.POST.get("status", "ACTIVE"),
            remarks=request.POST.get("remarks"),
        )

        return redirect(
            "volunteers:list"
        )

    return render(
        request,
        "volunteers/volunteer_form.html",
    )


def volunteer_detail(request, pk):

    volunteer = get_object_or_404(
        Volunteer,
        pk=pk
    )

    activities = volunteer.activities.all()

    participations = volunteer.event_participations.select_related(
        "event"
    )

    return render(
        request,
        "volunteers/volunteer_detail.html",
        {
            "volunteer": volunteer,
            "activities": activities,
            "participations": participations,
        },
    )


def activity_create(request, pk):

    volunteer = get_object_or_404(
        Volunteer,
        pk=pk
    )

    if request.method == "POST":

        VolunteerActivity.objects.create(
            volunteer=volunteer,
            activity_name=request.POST.get("activity_name"),
            activity_date=request.POST.get("activity_date"),
            description=request.POST.get("description"),
            status=request.POST.get(
                "status",
                "ASSIGNED"
            ),
            remarks=request.POST.get("remarks"),
        )

        return redirect(
            "volunteers:detail",
            pk=volunteer.pk
        )

    return render(
        request,
        "volunteers/activity_form.html",
        {
            "volunteer": volunteer,
        },
    )


def event_participation_create(request, pk):

    volunteer = get_object_or_404(
        Volunteer,
        pk=pk
    )

    events = Event.objects.all()

    if request.method == "POST":

        EventParticipation.objects.create(
            volunteer=volunteer,
            event_id=request.POST.get("event"),
            role=request.POST.get("role"),
            participation_status=request.POST.get(
                "participation_status",
                "ASSIGNED"
            ),
            hours_contributed=request.POST.get(
                "hours_contributed",
                0
            ),
            remarks=request.POST.get("remarks"),
        )

        return redirect(
            "volunteers:detail",
            pk=volunteer.pk
        )

    return render(
        request,
        "volunteers/event_participation_form.html",
        {
            "volunteer": volunteer,
            "events": events,
        },
    )