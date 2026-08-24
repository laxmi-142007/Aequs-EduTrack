from django import forms
from .models import Distribution
from students.models import Student
from schools.models import School
from inventory.models import InventoryItem
from eligibility.models import EligibilityRecord


class DistributionForm(forms.ModelForm):
    class Meta:
        model = Distribution
        fields = [
            "benefit_type",
            "student",
            "school",
            "inventory_item",
            "academic_year",
            "quantity",
            "issued_by",
            "remarks",
        ]
        widgets = {
            "benefit_type": forms.Select(attrs={"class": "form-control", "id": "id_benefit_type"}),
            "student": forms.Select(attrs={"class": "form-control", "id": "id_student"}),
            "school": forms.Select(attrs={"class": "form-control", "id": "id_school"}),
            "inventory_item": forms.Select(attrs={"class": "form-control", "id": "id_inventory_item"}),
            "academic_year": forms.TextInput(attrs={"class": "form-control", "placeholder": "Example: 2026-27"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1, "value": 1}),
            "issued_by": forms.TextInput(attrs={"class": "form-control", "placeholder": "Staff / Coordinator name"}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Distribution notes..."}),
        }

    def __init__(self, *args, skip_eligibility=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.skip_eligibility = skip_eligibility

        self.fields["student"].required = False
        self.fields["school"].required = False
        self.fields["inventory_item"].required = False

        # Student list is populated dynamically from the eligibility API
        # based on Benefit Type + Academic Year.
        self.fields["student"].queryset = (
            Student.objects.none()
        )

        self.fields["school"].queryset = (
            School.objects
            .all()
            .order_by("name")
        )

        self.fields["inventory_item"].queryset = (
            InventoryItem.objects
            .all()
            .order_by("item_name")
        )

    def clean(self):
        cleaned_data = super().clean()

        student = cleaned_data.get("student")
        school = cleaned_data.get("school")
        benefit_type = cleaned_data.get("benefit_type")
        academic_year = cleaned_data.get("academic_year")

        if not student and not school:
            raise forms.ValidationError(
                "Please select either a Student or a School as the recipient."
            )

        if student and not school:
            cleaned_data["school"] = student.school

        if not student or not benefit_type or not academic_year:
            return cleaned_data

        # Check eligibility unless explicitly skipped by the create view.
        if not self.skip_eligibility:
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

        # Check duplicate distribution.
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
