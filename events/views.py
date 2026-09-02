from django.shortcuts import render, redirect, get_object_or_404
from inventory.models import InventoryItem, StockTransaction
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
        inventory_item_id = request.POST.get("inventory_item")
        inventory_quantity = request.POST.get("inventory_quantity")

        event = Event.objects.create(
            title=title,
            description=description,
            event_date=event_date,
            location=location,
            organizer=organizer,
        )

        if inventory_item_id and inventory_quantity:
            try:
                qty = int(inventory_quantity)
                if qty > 0:
                    item = InventoryItem.objects.get(pk=inventory_item_id)
                    prev_stock = item.current_stock
                    new_stock = max(0, prev_stock - qty)
                    item.current_stock = new_stock
                    item.save()

                    StockTransaction.objects.create(
                        item=item,
                        transaction_type=StockTransaction.TransactionType.STOCK_OUT,
                        quantity=qty,
                        previous_stock=prev_stock,
                        new_stock=new_stock,
                        source_destination=f"Event: {event.title}",
                        reference_number=f"EVT-{event.pk}",
                        notes=f"Resource requested for event: {event.title}",
                    )

                    event.requested_item = item
                    event.requested_quantity = qty
                    event.save()
            except (ValueError, InventoryItem.DoesNotExist):
                pass

        return redirect("events:list")

    inventory_items = InventoryItem.objects.filter(status="ACTIVE")

    return render(
        request,
        "events/event_form.html",
        {
            "inventory_items": inventory_items,
        },
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

    inventory_items = InventoryItem.objects.filter(status="ACTIVE")

    return render(
        request,
        "events/event_form.html",
        {
            "event": event,
            "inventory_items": inventory_items,
            "is_edit": True,
        },
    )


def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        event.delete()

    return redirect("events:list")
