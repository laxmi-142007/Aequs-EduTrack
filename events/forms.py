from django import forms

from inventory.models import InventoryItem

from .models import Event


class PublicEventForm(forms.ModelForm):

    inventory_item = forms.ModelChoiceField(
        queryset=InventoryItem.objects.filter(
            status="ACTIVE"
        ),
        required=False,
        empty_label="No inventory item",
        label="Inventory Item",
    )

    inventory_quantity = forms.IntegerField(
        required=False,
        min_value=0,
        initial=0,
        label="Quantity Required",
    )

    class Meta:

        model = Event

        fields = [
            "title",
            "description",
            "event_date",
            "location",
            "organizer",
        ]

        labels = {
            "title": "Event Title",
            "description": "Description",
            "event_date": "Event Date",
            "location": "Location",
            "organizer": "Organizer",
        }

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "placeholder": "Enter event title",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "placeholder": "Enter event description",
                    "rows": 4,
                }
            ),

            "event_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "location": forms.TextInput(
                attrs={
                    "placeholder": "Enter event location",
                }
            ),

            "organizer": forms.TextInput(
                attrs={
                    "placeholder": "Enter organizer name",
                }
            ),
        }
