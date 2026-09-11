import csv
from io import BytesIO

try:
    import qrcode
except ImportError:
    qrcode = None

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from inventory.models import InventoryItem, StockTransaction
from reports.models import ActivityLog, log_activity
from volunteers.models import EventParticipation, Volunteer, VolunteerFormLink

from .forms import PublicEventForm
from .models import Event, EventFormLink, EventResource


def is_event_manager(user, event=None):
    """
    Returns True if user has coordinator/admin rights to create, edit, delete,
    or manage events and volunteer assignments.
    Normal volunteers (role == 'VOLUNTEER') always return False.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff or getattr(user, "is_admin", False):
        return True
    user_role = getattr(user, "role", "")
    if user_role in ["EVENT_COORDINATOR", "ADMIN", "SUPER_ADMIN"]:
        return True
    if user_role == "VOLUNTEER":
        return False
    if event and event.organizer:
        full_name = user.get_full_name().strip().lower()
        org = event.organizer.lower()
        if (full_name and full_name in org) or (user.username.lower() in org):
            return True
    return False


# =============================================================================
# EVENT LIST
# =============================================================================

@login_required
def event_list(request):
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    my_events_filter = request.GET.get("my_events", "").strip()

    events_qs = Event.objects.select_related("requested_item").prefetch_related(
        "volunteer_participations__volunteer", "resources__item"
    ).all()

    # KPI counts calculated across all records
    total_events = events_qs.count()
    upcoming_count = events_qs.filter(status=Event.Status.PLANNED).count()
    completed_count = events_qs.filter(status=Event.Status.COMPLETED).count()
    volunteers_mobilized = EventParticipation.objects.values("volunteer").distinct().count()

    # Identify current user's volunteer profile if authenticated
    current_volunteer = None
    user_participations_map = {}
    if request.user.is_authenticated:
        current_volunteer = Volunteer.objects.filter(user=request.user).first()
        if not current_volunteer and request.user.email:
            current_volunteer = Volunteer.objects.filter(email__iexact=request.user.email).first()
            if current_volunteer and not current_volunteer.user:
                current_volunteer.user = request.user
                current_volunteer.save(update_fields=["user"])

        if current_volunteer:
            parts = EventParticipation.objects.filter(volunteer=current_volunteer)
            user_participations_map = {p.event_id: p for p in parts}

    if q:
        events_qs = events_qs.filter(
            Q(title__icontains=q)
            | Q(location__icontains=q)
            | Q(organizer__icontains=q)
            | Q(description__icontains=q)
        )

    if status_filter:
        events_qs = events_qs.filter(status=status_filter)

    if my_events_filter == "1" and current_volunteer:
        events_qs = events_qs.filter(
            volunteer_participations__volunteer=current_volunteer
        ).exclude(volunteer_participations__participation_status="CANCELLED")

    # Attach participation state to each event object for template ease
    events_list = list(events_qs)
    for ev in events_list:
        ev.user_participation = user_participations_map.get(ev.id)

    campaigns = [ev for ev in events_list if ev.event_type == Event.EventType.CAMPAIGN]
    events_only = [ev for ev in events_list if ev.event_type != Event.EventType.CAMPAIGN]

    can_create_event = is_event_manager(request.user)
    form_links = EventFormLink.objects.filter(is_active=True)

    vol_link = VolunteerFormLink.objects.filter(is_active=True).order_by("-created_at").first()
    if not vol_link:
        vol_link = VolunteerFormLink.objects.create()
    volunteer_form_url = request.build_absolute_uri(f"/volunteers/form/{vol_link.token}/")
    volunteer_qr_url = request.build_absolute_uri(f"/volunteers/form/qr/{vol_link.token}/")

    today = timezone.now().date()
    from datetime import timedelta
    three_days = today + timedelta(days=3)
    due_reminder_events = [
        ev for ev in events_list
        if not ev.reminder_sent
        and ev.event_date >= today
        and ((ev.reminder_scheduled_date and ev.reminder_scheduled_date <= today) or ev.event_date <= three_days)
    ]

    return render(
        request,
        "events/event_list.html",
        {
            "events": events_list,
            "campaigns": campaigns,
            "events_only": events_only,
            "total_campaigns": len(campaigns),
            "total_events_only": len(events_only),
            "q": q,
            "status_filter": status_filter,
            "my_events_filter": my_events_filter,
            "current_volunteer": current_volunteer,
            "status_choices": Event.Status.choices,
            "total_events": total_events,
            "upcoming_count": upcoming_count,
            "completed_count": completed_count,
            "volunteers_mobilized": volunteers_mobilized,
            "can_create_event": can_create_event,
            "form_links": form_links,
            "volunteer_form_url": volunteer_form_url,
            "volunteer_qr_url": volunteer_qr_url,
            "due_reminder_events": due_reminder_events,
            "due_reminders_count": len(due_reminder_events),
        },
    )



# =============================================================================
# EVENT DETAIL
# =============================================================================

@login_required
def event_detail(request, pk):
    event = get_object_or_404(
        Event.objects.select_related("requested_item").prefetch_related(
            "volunteer_participations__volunteer", "resources__item"
        ),
        pk=pk,
    )
    participations = event.volunteer_participations.select_related("volunteer").all()
    assigned_volunteer_ids = participations.values_list("volunteer_id", flat=True)
    available_volunteers = Volunteer.objects.filter(status="ACTIVE").exclude(id__in=assigned_volunteer_ids)

    # Check current user volunteer profile and participation
    current_volunteer = None
    user_participation = None
    if request.user.is_authenticated:
        current_volunteer = Volunteer.objects.filter(user=request.user).first()
        if not current_volunteer and request.user.email:
            current_volunteer = Volunteer.objects.filter(email__iexact=request.user.email).first()
        if current_volunteer:
            user_participation = participations.filter(volunteer=current_volunteer).first()

    pending_requests = [p for p in participations if p.participation_status == "REQUESTED"]
    confirmed_volunteers = [p for p in participations if p.participation_status not in ["REQUESTED", "CANCELLED"]]

    # Check role permissions: normal volunteers cannot edit or delete events
    is_coordinator_or_admin = is_event_manager(request.user)
    can_edit_event = is_event_manager(request.user, event)
    can_delete_event = is_coordinator_or_admin
    can_manage_resources = is_event_manager(request.user, event)

    # Auto-sync legacy single requested_item into EventResource if not present
    if event.requested_item and not event.resources.filter(item=event.requested_item).exists():
        EventResource.objects.get_or_create(
            event=event,
            item=event.requested_item,
            defaults={"quantity": event.requested_quantity or 1},
        )

    event_resources = event.resources.select_related("item").all()
    inventory_items = InventoryItem.objects.filter(status="ACTIVE")

    return render(
        request,
        "events/event_detail.html",
        {
            "event": event,
            "participations": participations,
            "pending_requests": pending_requests,
            "confirmed_volunteers": confirmed_volunteers,
            "available_volunteers": available_volunteers,
            "current_volunteer": current_volunteer,
            "user_participation": user_participation,
            "is_coordinator_or_admin": is_coordinator_or_admin,
            "can_edit_event": can_edit_event,
            "can_delete_event": can_delete_event,
            "can_manage_resources": can_manage_resources,
            "inventory_items": inventory_items,
            "event_resources": event_resources,
            "participation_status_choices": EventParticipation.STATUS_CHOICES,
        },
    )


# =============================================================================
# VOLUNTEER SELF-ACTIONS & APPROVALS
# =============================================================================

@login_required
def event_volunteer_signup(request, pk):
    """Allow an authenticated volunteer to choose and request to volunteer for an event."""
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        volunteer = Volunteer.get_or_create_for_user(request.user)
        if not volunteer:
            messages.error(request, "Unable to find or create your volunteer profile.")
            return redirect("events:detail", pk=event.pk)

        role = request.POST.get("role", "").strip() or "Volunteer"
        remarks = request.POST.get("remarks", "").strip() or "Self-requested signup"

        participation, created = EventParticipation.objects.update_or_create(
            volunteer=volunteer,
            event=event,
            defaults={
                "role": role,
                "participation_status": "REQUESTED",
                "remarks": remarks,
            },
        )
        messages.success(
            request,
            f"Your request to volunteer for '{event.title}' has been submitted for coordinator approval.",
        )
    return redirect("events:detail", pk=event.pk)


@login_required
def event_volunteer_withdraw(request, pk):
    """Allow a volunteer to cancel their request or withdraw from an event."""
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        volunteer = Volunteer.objects.filter(user=request.user).first() or (
            Volunteer.objects.filter(email__iexact=request.user.email).first() if request.user.email else None
        )
        if volunteer:
            participation = EventParticipation.objects.filter(event=event, volunteer=volunteer).first()
            if participation:
                participation.participation_status = "CANCELLED"
                participation.save()
                messages.info(request, f"You have withdrawn from '{event.title}'.")
            else:
                messages.warning(request, "You are not registered for this event.")
        else:
            messages.error(request, "Volunteer profile not found.")
    return redirect("events:detail", pk=event.pk)


@login_required
def event_approve_volunteer(request, pk, participation_id):
    """Event coordinator/admin approves a volunteer's sign-up request."""
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        participation = get_object_or_404(EventParticipation, pk=participation_id, event=event)
        participation.participation_status = "ASSIGNED"
        participation.save()
        messages.success(request, f"Volunteer request for {participation.volunteer} approved.")
    return redirect("events:detail", pk=event.pk)


@login_required
def event_decline_volunteer(request, pk, participation_id):
    """Event coordinator/admin declines a volunteer's sign-up request."""
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        participation = get_object_or_404(EventParticipation, pk=participation_id, event=event)
        participation.participation_status = "CANCELLED"
        participation.save()
        messages.info(request, f"Volunteer request for {participation.volunteer} has been declined.")
    return redirect("events:detail", pk=event.pk)


@login_required
def event_assign_volunteer(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.user.is_authenticated and not is_event_manager(request.user, event):
        messages.error(request, "Permission denied. Normal volunteers are not authorized to assign volunteers.")
        return redirect("events:detail", pk=event.pk)

    if request.method == "POST":
        volunteer_id = request.POST.get("volunteer")
        role = request.POST.get("role", "").strip()
        status = request.POST.get("participation_status", "ASSIGNED")
        hours = request.POST.get("hours_contributed", 0)
        remarks = request.POST.get("remarks", "").strip()

        if volunteer_id:
            volunteer = get_object_or_404(Volunteer, pk=volunteer_id)
            try:
                hours_val = float(hours) if hours else 0
            except ValueError:
                hours_val = 0

            participation, created = EventParticipation.objects.update_or_create(
                volunteer=volunteer,
                event=event,
                defaults={
                    "role": role,
                    "participation_status": status,
                    "hours_contributed": hours_val,
                    "remarks": remarks,
                },
            )
            action_text = "assigned to" if created else "updated for"
            messages.success(request, f"Volunteer {volunteer.first_name} {volunteer.last_name} {action_text} this event.")
        else:
            messages.error(request, "Please select a valid volunteer.")

    return redirect("events:detail", pk=event.pk)


@login_required
def event_remove_volunteer(request, pk, participation_id):
    event = get_object_or_404(Event, pk=pk)

    if request.user.is_authenticated and not is_event_manager(request.user, event):
        messages.error(request, "Permission denied. Normal volunteers are not authorized to remove volunteers.")
        return redirect("events:detail", pk=event.pk)

    if request.method == "POST":
        participation = get_object_or_404(EventParticipation, pk=participation_id, event=event)
        v_name = str(participation.volunteer)
        participation.delete()
        messages.success(request, f"Volunteer {v_name} removed from this event.")

    return redirect("events:detail", pk=event.pk)


# =============================================================================
# EVENT & CAMPAIGN CREATION / EDITING
# =============================================================================

def _save_event_or_campaign(request, is_campaign=False, pk=None):
    event = None
    if pk:
        event = get_object_or_404(Event, pk=pk)
        if request.user.is_authenticated and not is_event_manager(request.user, event):
            messages.error(request, "Permission denied. You are not authorized to edit this record.")
            return redirect("events:detail", pk=event.pk)
    else:
        if request.user.is_authenticated and not is_event_manager(request.user):
            messages.error(request, "Permission denied. Normal volunteers are not authorized to create this record.")
            return redirect("events:list")

    entity_name = "Campaign" if is_campaign else "Event"
    entity_type = Event.EventType.CAMPAIGN if is_campaign else Event.EventType.EVENT

    if request.method == "POST":
        title = request.POST.get("title")
        status = request.POST.get("status", Event.Status.PLANNED if not event else event.status)
        description = request.POST.get("description", "")
        event_date = request.POST.get("event_date")
        location = request.POST.get("location", "")
        organizer = request.POST.get("organizer", "")

        inventory_item_id = request.POST.get("inventory_item")
        inventory_quantity = request.POST.get("inventory_quantity")
        reminder_scheduled_date = request.POST.get("reminder_scheduled_date") or None
        if not reminder_scheduled_date and event_date:
            try:
                from datetime import timedelta
                parsed_d = timezone.datetime.strptime(event_date, "%Y-%m-%d").date()
                reminder_scheduled_date = parsed_d - timedelta(days=1)
            except Exception:
                pass

        with transaction.atomic():
            if not event:
                event = Event.objects.create(
                    title=title,
                    event_type=entity_type,
                    status=status,
                    description=description,
                    event_date=event_date,
                    location=location,
                    organizer=organizer,
                    reminder_scheduled_date=reminder_scheduled_date,
                )
                action_text = f"{entity_name} created: {event.title}"
                action_type = ActivityLog.ActionType.CREATE
            else:
                event.title = title
                event.event_type = entity_type
                event.status = status
                event.description = description
                event.event_date = event_date
                event.location = location
                event.organizer = organizer
                if reminder_scheduled_date:
                    event.reminder_scheduled_date = reminder_scheduled_date
                event.save()
                action_text = f"{entity_name} updated: {event.title}"
                action_type = ActivityLog.ActionType.UPDATE

            if inventory_item_id and inventory_quantity:
                try:
                    qty = int(inventory_quantity)
                    if qty > 0:
                        item = InventoryItem.objects.select_for_update().get(pk=inventory_item_id)
                        prev_stock = item.current_stock
                        deduct_qty = qty
                        if pk and event.requested_item_id == item.id:
                            deduct_qty = max(0, qty - (event.requested_quantity or 0))

                        if deduct_qty > 0:
                            actual_deduct = min(deduct_qty, prev_stock)
                            new_stock = max(0, prev_stock - actual_deduct)
                            item.current_stock = new_stock
                            item.save(update_fields=["current_stock"])
                            StockTransaction.objects.create(
                                item=item,
                                transaction_type=StockTransaction.TransactionType.STOCK_OUT,
                                quantity=actual_deduct,
                                previous_stock=prev_stock,
                                new_stock=new_stock,
                                source_destination=f"{entity_name}: {event.title}",
                                reference_number=f"EVT-{event.pk}",
                                notes=f"Resource for {entity_name.lower()}: {event.title}",
                            )
                        event.requested_item = item
                        event.requested_quantity = qty
                        event.save(update_fields=["requested_item", "requested_quantity"])
                        EventResource.objects.update_or_create(
                            event=event,
                            item=item,
                            defaults={"quantity": qty},
                        )
                except (ValueError, InventoryItem.DoesNotExist):
                    pass

            log_activity(
                request,
                action=action_text,
                category="EVENT",
                action_type=action_type,
                object_type="Event",
                object_id=event.pk,
                details=f"{entity_name} '{event.title}' was {'updated' if pk else 'created'}.",
            )

        messages.success(request, f"{entity_name} '{event.title}' {'updated' if pk else 'scheduled'} successfully.")
        return redirect("events:detail", pk=event.pk)

    inventory_items = InventoryItem.objects.filter(status="ACTIVE")
    template_name = "events/campaign_form.html" if is_campaign else "events/event_form.html"

    return render(
        request,
        template_name,
        {
            "event": event,
            "is_campaign": is_campaign,
            "page_title": f"{'Edit' if pk else 'Schedule New'} {entity_name}" + (f": {event.title}" if event else ""),
            "form_title": f"{'Update' if pk else 'Schedule'} {entity_name} Details",
            "inventory_items": inventory_items,
            "status_choices": Event.Status.choices,
            "is_edit": bool(pk),
        },
    )


@login_required
def event_create(request):
    return _save_event_or_campaign(request, is_campaign=False)


@login_required
def campaign_create(request):
    return _save_event_or_campaign(request, is_campaign=True)


@login_required
def event_edit(request, pk):
    return _save_event_or_campaign(request, is_campaign=False, pk=pk)


@login_required
def campaign_edit(request, pk):
    return _save_event_or_campaign(request, is_campaign=True, pk=pk)


# =============================================================================
# RESOURCE ALLOCATION (MULTI-ITEM)
# =============================================================================

@login_required
def event_add_resource(request, pk):
    """Allow authorized coordinator, admin, or organizer to allocate inventory resources to the event."""
    event = get_object_or_404(Event, pk=pk)

    if not is_event_manager(request.user, event):
        messages.error(request, "Permission denied. Normal volunteers are not authorized to allocate event resources.")
        return redirect("events:detail", pk=event.pk)

    if request.method == "POST":
        item_id = request.POST.get("inventory_item")
        qty_str = request.POST.get("inventory_quantity", "").strip()

        try:
            qty = int(qty_str) if qty_str else 0
        except ValueError:
            qty = 0

        if item_id and qty > 0:
            item = get_object_or_404(InventoryItem, pk=item_id)
            prev_stock = item.current_stock
            new_stock = max(0, prev_stock - qty)
            item.current_stock = new_stock
            item.save(update_fields=["current_stock"])

            StockTransaction.objects.create(
                item=item,
                transaction_type=StockTransaction.TransactionType.STOCK_OUT,
                quantity=qty,
                previous_stock=prev_stock,
                new_stock=new_stock,
                source_destination=f"Event: {event.title}",
                reference_number=f"EVT-{event.pk}",
                notes=f"Resource allocated for event: {event.title} by {request.user.username}",
            )

            res, created = EventResource.objects.get_or_create(
                event=event,
                item=item,
                defaults={"quantity": qty},
            )
            if not created:
                res.quantity += qty
                res.save(update_fields=["quantity"])

            if not event.requested_item:
                event.requested_item = item
                event.requested_quantity = qty
            elif event.requested_item_id == item.id:
                event.requested_quantity = (event.requested_quantity or 0) + qty
            event.save(update_fields=["requested_item", "requested_quantity"])

            messages.success(request, f"Successfully allocated {qty} × {item.item_name} to this event.")
        else:
            messages.error(request, "Please select an inventory item and enter a quantity greater than 0.")

    return redirect("events:detail", pk=event.pk)


@login_required
def event_remove_resource(request, pk, resource_id):
    """Allow removing an allocated resource from the event, returning stock to the warehouse."""
    event = get_object_or_404(Event, pk=pk)

    if not is_event_manager(request.user, event):
        messages.error(request, "Permission denied. Normal volunteers are not authorized to remove event resources.")
        return redirect("events:detail", pk=event.pk)

    if request.method == "POST":
        res = get_object_or_404(EventResource, pk=resource_id, event=event)
        item = res.item
        qty = res.quantity

        prev_stock = item.current_stock
        new_stock = prev_stock + qty
        item.current_stock = new_stock
        item.save(update_fields=["current_stock"])

        StockTransaction.objects.create(
            item=item,
            transaction_type=StockTransaction.TransactionType.STOCK_IN,
            quantity=qty,
            previous_stock=prev_stock,
            new_stock=new_stock,
            source_destination=f"Returned from Event: {event.title}",
            reference_number=f"EVT-RET-{event.pk}",
            notes=f"Resource allocation returned/cancelled for event: {event.title} by {request.user.username}",
        )

        res.delete()

        # Sync legacy requested_item
        if event.requested_item_id == item.id:
            next_res = event.resources.first()
            if next_res:
                event.requested_item = next_res.item
                event.requested_quantity = next_res.quantity
            else:
                event.requested_item = None
                event.requested_quantity = 0
            event.save(update_fields=["requested_item", "requested_quantity"])

        messages.info(request, f"Removed {item.item_name} from event and returned {qty} to warehouse inventory.")

    return redirect("events:detail", pk=event.pk)


# =============================================================================
# EVENT DELETE
# =============================================================================

@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.user.is_authenticated and not is_event_manager(request.user, event):
        messages.error(request, "Permission denied. Normal volunteers are not authorized to delete events.")
        return redirect("events:detail", pk=event.pk)

    if request.method == "POST":
        event_title = event.title
        event_id = event.pk
        event.delete()

        log_activity(
            request,
            action=f"Event deleted: {event_title}",
            category="EVENT",
            action_type=ActivityLog.ActionType.DELETE,
            object_type="Event",
            object_id=event_id,
            details=f"Event '{event_title}' was deleted.",
        )
        messages.success(request, f"Event '{event_title}' was deleted.")
        return redirect("events:list")

    return redirect("events:detail", pk=event.pk)


# =============================================================================
# EXPORTS
# =============================================================================

def event_export_csv(request):
    events = Event.objects.select_related("requested_item").all()
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if q:
        events = events.filter(
            Q(title__icontains=q)
            | Q(location__icontains=q)
            | Q(organizer__icontains=q)
        )
    if status_filter:
        events = events.filter(status=status_filter)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="aequs_events.csv"'

    writer = csv.writer(response)
    writer.writerow(["ID", "Title", "Status", "Event Date", "Location", "Organizer", "Requested Item", "Quantity", "Volunteers"])

    for e in events:
        item_name = e.requested_item.item_name if e.requested_item else "None"
        writer.writerow([
            e.id,
            e.title,
            e.get_status_display(),
            e.event_date.strftime("%Y-%m-%d") if e.event_date else "",
            e.location,
            e.organizer,
            item_name,
            e.requested_quantity,
            e.volunteer_count,
        ])

    return response


def event_export_excel(request):
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    events = Event.objects.select_related("requested_item").all()
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if q:
        events = events.filter(
            Q(title__icontains=q)
            | Q(location__icontains=q)
            | Q(organizer__icontains=q)
        )
    if status_filter:
        events = events.filter(status=status_filter)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Aequs Events"

    title_font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    meta_font = Font(name="Calibri", size=10, italic=True, color="64748B")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="DD2D27", end_color="DD2D27", fill_type="solid")
    border_side = Side(border_style="thin", color="E2E8F0")
    cell_border = Border(top=border_side, bottom=border_side, left=border_side, right=border_side)

    ws.append(["Aequs Foundation - Events Directory"])
    ws.cell(row=1, column=1).font = title_font
    ws.append([f"Exported: {len(events)} events | Status Filter: {status_filter or 'All'}"])
    ws.cell(row=2, column=1).font = meta_font
    ws.append([])

    headers = ["ID", "Event Title", "Status", "Date", "Location", "Organizer", "Allocated Item", "Qty", "Volunteers"]
    ws.append(headers)
    header_row_idx = ws.max_row
    for col_idx in range(1, len(headers) + 1):
        c = ws.cell(row=header_row_idx, column=col_idx)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center" if headers[col_idx-1] in ["ID", "Status", "Date", "Qty", "Volunteers"] else "left")

    for e in events:
        item_name = e.requested_item.item_name if e.requested_item else "—"
        ws.append([
            e.id,
            e.title,
            e.get_status_display(),
            e.event_date.strftime("%Y-%m-%d") if e.event_date else "—",
            e.location or "—",
            e.organizer or "—",
            item_name,
            e.requested_quantity,
            e.volunteer_count,
        ])
        curr_row = ws.max_row
        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(row=curr_row, column=col_idx)
            c.border = cell_border

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    response = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="aequs_events.xlsx"'
    return response


# =============================================================================
# CREATE EVENT FORM LINK
# =============================================================================

@login_required
def create_event_form_link(request):
    if request.method == "POST":
        form_link = EventFormLink.objects.create()
        return redirect("events:share_form", pk=form_link.pk)

    return render(request, "events/create_form_link.html")


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

    form_url = request.build_absolute_uri(f"/events/form/{form_link.token}/")

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

    form_url = request.build_absolute_uri(f"/events/form/{form_link.token}/")

    if not qrcode:
        return HttpResponse("QR code generation library is not installed.", status=501)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(form_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )
    response["Content-Disposition"] = f'inline; filename="event-form-{pk}.png"'
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
        form = PublicEventForm(request.POST)

        if form.is_valid():
            inventory_item = form.cleaned_data.get("inventory_item")
            quantity = form.cleaned_data.get("inventory_quantity") or 0

            with transaction.atomic():
                event = form.save(commit=False)

                if inventory_item and quantity > 0:
                    item = InventoryItem.objects.select_for_update().get(pk=inventory_item.pk)

                    if quantity > item.current_stock:
                        form.add_error(
                            "inventory_quantity",
                            f"Only {item.current_stock} items are available.",
                        )
                    else:
                        previous_stock = item.current_stock
                        new_stock = previous_stock - quantity
                        item.current_stock = new_stock
                        item.save()

                        event.requested_item = item
                        event.requested_quantity = quantity
                        event.save()

                        StockTransaction.objects.create(
                            item=item,
                            transaction_type=StockTransaction.TransactionType.STOCK_OUT,
                            quantity=quantity,
                            previous_stock=previous_stock,
                            new_stock=new_stock,
                            source_destination=f"Event: {event.title}",
                            reference_number=f"EVT-{event.pk}",
                            notes=f"Resource requested through public event form: {event.title}",
                        )

                        EventResource.objects.get_or_create(
                            event=event,
                            item=item,
                            defaults={"quantity": quantity},
                        )
                else:
                    event.save()

                if form.errors:
                    return render(
                        request,
                        "events/public_event_form.html",
                        {
                            "form": form,
                            "form_link": form_link,
                        },
                    )

                log_activity(
                    request,
                    action=f"Event created: {event.title}",
                    category="EVENT",
                    action_type=ActivityLog.ActionType.CREATE,
                    object_type="Event",
                    object_id=event.pk,
                    details="Event created through public employee event form.",
                )

            return redirect("events:success", pk=event.pk)
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
    event = get_object_or_404(Event, pk=pk)
    return render(
        request,
        "events/event_success.html",
        {
            "event": event,
        },
    )


# =============================================================================
# EVENT REMINDER FEATURE (Module 10)
# =============================================================================

@login_required
def event_send_reminder(request, pk):
    """
    Module 10: Event Reminder Feature.
    Dispatches automated event reminder alerts to organizers and volunteers.
    """
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        event.reminder_sent = True
        event.reminder_scheduled_date = timezone.now().date()
        event.save(update_fields=["reminder_sent", "reminder_scheduled_date"])
        vol_count = event.volunteer_participations.count()
        messages.success(
            request,
            f"Event reminder sent for '{event.title}'. Notified organizer and {vol_count} registered volunteer(s)."
        )
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("events:detail", pk=event.pk)


@login_required
def event_send_all_due_reminders(request):
    """
    Module 10: Dispatches reminders for all upcoming events whose reminder date has arrived
    or is within 3 days and reminder hasn't been sent yet.
    """
    if request.method == "POST":
        today = timezone.now().date()
        from datetime import timedelta
        three_days = today + timedelta(days=3)

        due_events = Event.objects.filter(
            reminder_sent=False,
            event_date__gte=today,
        ).filter(
            Q(reminder_scheduled_date__lte=today) |
            Q(reminder_scheduled_date__isnull=True, event_date__lte=three_days)
        )

        count = 0
        total_volunteers = 0
        for ev in due_events:
            ev.reminder_sent = True
            if not ev.reminder_scheduled_date:
                ev.reminder_scheduled_date = today
            ev.save(update_fields=["reminder_sent", "reminder_scheduled_date"])
            count += 1
            total_volunteers += ev.volunteer_participations.count()

        if count > 0:
            messages.success(
                request,
                f"Automated Reminders sent for {count} event(s)! Notified organizers and {total_volunteers} volunteer(s)."
            )
        else:
            messages.info(request, "All upcoming event reminders are already up to date.")

    next_url = request.POST.get("next") or request.GET.get("next") or "events:list"
    return redirect(next_url)


