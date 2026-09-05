from io import BytesIO

import qrcode

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from inventory.models import (
    InventoryItem,
    StockTransaction,
)

from reports.models import (
    ActivityLog,
    log_activity,
)

from .models import (
    Event,
    EventFormLink,
)

from .forms import PublicEventForm


# =============================================================================
# EVENT LIST
# =============================================================================

@login_required
def event_list(request):

    events = Event.objects.all()

    form_links = EventFormLink.objects.filter(
        is_active=True
    )

    return render(
        request,
        "events/event_list.html",
        {
            "events": events,
            "form_links": form_links,
        },
    )


# =============================================================================
# NORMAL EVENT CREATE
# =============================================================================

@login_required
def event_create(request):

    if request.method == "POST":

        title = request.POST.get("title")
        description = request.POST.get("description")
        event_date = request.POST.get("event_date")
        location = request.POST.get("location")
        organizer = request.POST.get("organizer")

        inventory_item_id = request.POST.get(
            "inventory_item"
        )

        inventory_quantity = request.POST.get(
            "inventory_quantity"
        )

        with transaction.atomic():

            event = Event.objects.create(
                title=title,
                description=description,
                event_date=event_date,
                location=location,
                organizer=organizer,
            )

            if inventory_item_id and inventory_quantity:

                try:

                    qty = int(
                        inventory_quantity
                    )

                    if qty > 0:

                        item = (
                            InventoryItem.objects
                            .select_for_update()
                            .get(
                                pk=inventory_item_id
                            )
                        )

                        previous_stock = (
                            item.current_stock
                        )

                        if qty > previous_stock:
                            qty = previous_stock

                        new_stock = (
                            previous_stock - qty
                        )

                        item.current_stock = new_stock

                        item.save()

                        StockTransaction.objects.create(
                            item=item,

                            transaction_type=(
                                StockTransaction
                                .TransactionType
                                .STOCK_OUT
                            ),

                            quantity=qty,

                            previous_stock=previous_stock,

                            new_stock=new_stock,

                            source_destination=(
                                f"Event: {event.title}"
                            ),

                            reference_number=(
                                f"EVT-{event.pk}"
                            ),

                            notes=(
                                "Resource requested "
                                f"for event: {event.title}"
                            ),
                        )

                        event.requested_item = item

                        event.requested_quantity = qty

                        event.save()

                except (
                    ValueError,
                    InventoryItem.DoesNotExist,
                ):
                    pass

            # -------------------------------------------------------------
            # AUDIT LOG
            # -------------------------------------------------------------

            log_activity(
                request,
                action=f"Event created: {event.title}",
                category="EVENT",
                action_type=(
                    ActivityLog.ActionType.CREATE
                ),
                object_type="Event",
                object_id=event.pk,
                details=(
                    f"Event '{event.title}' "
                    "was created."
                ),
            )

        return redirect(
            "events:list"
        )

    inventory_items = (
        InventoryItem.objects
        .filter(status="ACTIVE")
    )

    return render(
        request,
        "events/event_form.html",
        {
            "inventory_items": inventory_items,
        },
    )


# =============================================================================
# EDIT EVENT
# =============================================================================

@login_required
def event_edit(request, pk):

    event = get_object_or_404(
        Event,
        pk=pk,
    )

    if request.method == "POST":

        event.title = request.POST.get(
            "title"
        )

        event.description = request.POST.get(
            "description"
        )

        event.event_date = request.POST.get(
            "event_date"
        )

        event.location = request.POST.get(
            "location"
        )

        event.organizer = request.POST.get(
            "organizer"
        )

        event.save()

        log_activity(
            request,
            action=f"Event updated: {event.title}",
            category="EVENT",
            action_type=(
                ActivityLog.ActionType.UPDATE
            ),
            object_type="Event",
            object_id=event.pk,
            details=(
                f"Event '{event.title}' "
                "was updated."
            ),
        )

        return redirect(
            "events:list"
        )

    inventory_items = (
        InventoryItem.objects
        .filter(status="ACTIVE")
    )

    return render(
        request,
        "events/event_form.html",
        {
            "event": event,
            "inventory_items": inventory_items,
            "is_edit": True,
        },
    )


# =============================================================================
# DELETE EVENT
# =============================================================================

@login_required
def event_delete(request, pk):

    event = get_object_or_404(
        Event,
        pk=pk,
    )

    if request.method == "POST":

        event_title = event.title
        event_id = event.pk

        event.delete()

        log_activity(
            request,
            action=f"Event deleted: {event_title}",
            category="EVENT",
            action_type=(
                ActivityLog.ActionType.DELETE
            ),
            object_type="Event",
            object_id=event_id,
            details=(
                f"Event '{event_title}' "
                "was deleted."
            ),
        )

    return redirect(
        "events:list"
    )


# =============================================================================
# CREATE EVENT FORM LINK
# =============================================================================

@login_required
def create_event_form_link(request):

    if request.method == "POST":

        form_link = EventFormLink.objects.create()

        return redirect(
            "events:share_form",
            pk=form_link.pk,
        )

    return render(
        request,
        "events/create_form_link.html",
    )


# =============================================================================
# SHARE EVENT FORM
# =============================================================================

@login_required
def share_event_form(request, pk):

    form_link = get_object_or_404(
        EventFormLink,
        pk=pk,
        is_active=True,
    )

    form_url = request.build_absolute_uri(
        f"/events/form/{form_link.token}/"
    )

    return render(
        request,
        "events/share_form.html",
        {
            "form_link": form_link,
            "form_url": form_url,
        },
    )


# =============================================================================
# EVENT FORM QR CODE
# =============================================================================

@login_required
def event_form_qr(request, pk):

    form_link = get_object_or_404(
        EventFormLink,
        pk=pk,
        is_active=True,
    )

    form_url = request.build_absolute_uri(
        f"/events/form/{form_link.token}/"
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(form_url)

    qr.make(
        fit=True
    )

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

    response["Content-Disposition"] = (
        f'inline; filename="event-form-{pk}.png"'
    )

    return response


# =============================================================================
# PUBLIC EMPLOYEE EVENT FORM
# =============================================================================

def public_event_form(request, token):

    form_link = get_object_or_404(
        EventFormLink,
        token=token,
        is_active=True,
    )

    if request.method == "POST":

        form = PublicEventForm(
            request.POST
        )

        if form.is_valid():

            inventory_item = (
                form.cleaned_data.get(
                    "inventory_item"
                )
            )

            quantity = (
                form.cleaned_data.get(
                    "inventory_quantity"
                )
                or 0
            )

            with transaction.atomic():

                # ---------------------------------------------------------
                # CREATE EVENT
                # ---------------------------------------------------------

                event = form.save(
                    commit=False
                )

                # ---------------------------------------------------------
                # INVENTORY
                # ---------------------------------------------------------

                if inventory_item and quantity > 0:

                    item = (
                        InventoryItem.objects
                        .select_for_update()
                        .get(
                            pk=inventory_item.pk
                        )
                    )

                    # -----------------------------------------------------
                    # CHECK STOCK
                    # -----------------------------------------------------

                    if quantity > item.current_stock:

                        form.add_error(
                            "inventory_quantity",
                            (
                                f"Only "
                                f"{item.current_stock} "
                                "items are available."
                            ),
                        )

                    else:

                        previous_stock = (
                            item.current_stock
                        )

                        new_stock = (
                            previous_stock
                            - quantity
                        )

                        item.current_stock = (
                            new_stock
                        )

                        item.save()

                        # -------------------------------------------------
                        # EVENT INVENTORY DETAILS
                        # -------------------------------------------------

                        event.requested_item = item

                        event.requested_quantity = (
                            quantity
                        )

                        event.save()

                        # -------------------------------------------------
                        # STOCK TRANSACTION
                        # -------------------------------------------------

                        StockTransaction.objects.create(
                            item=item,

                            transaction_type=(
                                StockTransaction
                                .TransactionType
                                .STOCK_OUT
                            ),

                            quantity=quantity,

                            previous_stock=(
                                previous_stock
                            ),

                            new_stock=new_stock,

                            source_destination=(
                                f"Event: {event.title}"
                            ),

                            reference_number=(
                                f"EVT-{event.pk}"
                            ),

                            notes=(
                                "Resource requested "
                                "through public event "
                                f"form: {event.title}"
                            ),
                        )

                else:

                    event.save()

                # ---------------------------------------------------------
                # IF FORM HAS ERROR
                # ---------------------------------------------------------

                if form.errors:

                    return render(
                        request,
                        "events/public_event_form.html",
                        {
                            "form": form,
                            "form_link": form_link,
                        },
                    )

                # ---------------------------------------------------------
                # AUDIT LOG
                # ---------------------------------------------------------

                log_activity(
                    request,
                    action=(
                        f"Event created: "
                        f"{event.title}"
                    ),
                    category="EVENT",
                    action_type=(
                        ActivityLog
                        .ActionType
                        .CREATE
                    ),
                    object_type="Event",
                    object_id=event.pk,
                    details=(
                        "Event created through "
                        "public employee event "
                        "form."
                    ),
                )

            return redirect(
                "events:success",
                pk=event.pk,
            )

    else:

        form = PublicEventForm()

    return render(
        request,
        "events/public_event_form.html",
        {
            "form": form,
            "form_link": form_link,
        },
    )


# =============================================================================
# EVENT SUCCESS PAGE
# =============================================================================

def event_success(request, pk):

    event = get_object_or_404(
        Event,
        pk=pk,
    )

    return render(
        request,
        "events/event_success.html",
        {
            "event": event,
        },
    )
