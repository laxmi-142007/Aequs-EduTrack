from django import forms
from .models import Distribution
from students.models import Student
from schools.models import School
from inventory.models import InventoryItem


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].required = False
        self.fields["school"].required = False
        self.fields["inventory_item"].required = False
        self.fields["student"].queryset = Student.objects.select_related("school").all().order_by("student_name")
        self.fields["school"].queryset = School.objects.all().order_by("name")
        self.fields["inventory_item"].queryset = InventoryItem.objects.all().order_by("item_name")

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get("student")
        school = cleaned_data.get("school")
        benefit_type = cleaned_data.get("benefit_type")

        if not student and not school:
            raise forms.ValidationError("Please select either a Student or a School as the recipient.")

        if student and not school:
            cleaned_data["school"] = student.school

        return cleaned_data