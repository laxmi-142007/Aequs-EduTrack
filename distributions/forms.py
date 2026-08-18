from django import forms
from .models import Distribution
from eligibility.models import EligibilityRecord


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

    def clean(self):
        cleaned_data = super().clean()

        student = cleaned_data.get("student")
        benefit_type = cleaned_data.get("benefit_type")
        academic_year = cleaned_data.get("academic_year")

        if not student or not benefit_type or not academic_year:
            return cleaned_data

        # ==========================================
        # CHECK ELIGIBILITY
        # ==========================================

        eligible = EligibilityRecord.objects.filter(
            student=student,
            benefit_type=benefit_type,
            academic_year=academic_year,
            eligible=True,
        ).exists()

        if not eligible:
            raise forms.ValidationError(
                f"{student.student_name} is not eligible for "
                f"{benefit_type} for academic year "
                f"{academic_year}."
            )

        # ==========================================
        # CHECK DUPLICATE DISTRIBUTION
        # ==========================================

        already_distributed = Distribution.objects.filter(
            student=student,
            benefit_type=benefit_type,
            academic_year=academic_year,
        ).exists()

        if already_distributed:
            raise forms.ValidationError(
                f"{student.student_name} has already received "
                f"{benefit_type} for academic year "
                f"{academic_year}."
            )

        return cleaned_data
