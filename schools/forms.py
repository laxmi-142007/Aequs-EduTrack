from django import forms
from .models import School


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = [
            "name",
            "udise_code",
            "address",
            "district",
            "taluk",
            "village",
            "pincode",
            "phone",
            "email",
            "headmaster_name",
            "headmaster_phone",
            "student_strength",
            "established_year",
            "status",
        ]

        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }