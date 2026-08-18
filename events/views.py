from django.shortcuts import render, redirect

from .models import Event


def event_list(request):

    events = Event.objects.all()

    return render(
        request,
        "events/event_list.html",
        {
            "events": events,
        },
    )


def event_create(request):

    if request.method == "POST":

        title = request.POST.get("title")
        description = request.POST.get("description")
        event_date = request.POST.get("event_date")
        location = request.POST.get("location")
        organizer = request.POST.get("organizer")

        Event.objects.create(
            title=title,
            description=description,
            event_date=event_date,
            location=location,
            organizer=organizer,
        )

        return redirect("events:list")

    return render(
        request,
        "events/event_form.html",
    )
