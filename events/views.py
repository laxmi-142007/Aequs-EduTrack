from django.shortcuts import render, redirect, get_object_or_404

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


def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":

        event.title = request.POST.get("title")
        event.description = request.POST.get("description")
        event.event_date = request.POST.get("event_date")
        event.location = request.POST.get("location")
        event.organizer = request.POST.get("organizer")

        event.save()

        return redirect("events:list")

    return render(
        request,
        "events/event_form.html",
        {
            "event": event,
            "is_edit": True,
        },
    )


def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        event.delete()

    return redirect("events:list")
