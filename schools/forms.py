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
            "address": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Enter school address",
            }),

            "name": forms.TextInput(attrs={
                "placeholder": "Enter school name",
            }),

            "udise_code": forms.TextInput(attrs={
                "placeholder": "Enter UDISE code",
            }),

            "district": forms.TextInput(attrs={
                "placeholder": "Enter district",
            }),

            "taluk": forms.TextInput(attrs={
                "placeholder": "Enter taluk",
            }),

            "village": forms.TextInput(attrs={
                "placeholder": "Enter village",
            }),

            "pincode": forms.TextInput(attrs={
                "placeholder": "Enter pincode",
            }),

            "phone": forms.TextInput(attrs={
                "placeholder": "Enter school phone",
            }),

            "email": forms.EmailInput(attrs={
                "placeholder": "Enter school email",
            }),

            "headmaster_name": forms.TextInput(attrs={
                "placeholder": "Enter headmaster name",
            }),

            "headmaster_phone": forms.TextInput(attrs={
                "placeholder": "Enter headmaster phone",
            }),

            "student_strength": forms.NumberInput(attrs={
                "min": 0,
                "placeholder": "Enter student strength",
            }),

            "established_year": forms.NumberInput(attrs={
                "min": 1800,
                "max": 2100,
                "placeholder": "Enter established year",
            }),
        }