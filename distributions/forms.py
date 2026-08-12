from django import forms
from .models import Distribution


class DistributionForm(forms.ModelForm):

    class Meta:
        model = Distribution

        fields = [
            "student",
            "benefit_type",
            "academic_year",
            "quantity",
            "issued_by",
            "remarks",
        ]

        widgets = {
            "student": forms.Select(
                attrs={"class": "form-control"}
            ),

            "benefit_type": forms.Select(
                attrs={"class": "form-control"}
            ),

            "academic_year": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 2026-27",
                }
            ),

            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),

            "issued_by": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Staff / Volunteer name",
                }
            ),

            "remarks": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }