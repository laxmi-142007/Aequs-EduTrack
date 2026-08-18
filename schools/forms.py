from django import forms
from .models import School, SchoolMilestone, SchoolResource, GradeStrength


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
            "website",
            "headmaster_name",
            "headmaster_phone",
            "headmaster_qualification",
            "headmaster_experience",
            "headmaster_photo",
            "affiliation",
            "student_strength",
            "established_date",
            "established_year",
            "status",
        ]

        widgets = {
            "address": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Enter school address",
            }),
            "established_date": forms.DateInput(attrs={"type": "date"}),
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


class QuickSchoolCreateForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "village", "district", "established_date"]
        widgets = {
            "established_date": forms.DateInput(attrs={"type": "date"}),
        }


class SchoolMilestoneForm(forms.ModelForm):
    class Meta:
        model = SchoolMilestone
        fields = ["title", "year_or_date", "details", "impact"]
        widgets = {
            "details": forms.Textarea(attrs={"rows": 2}),
            "impact": forms.Textarea(attrs={"rows": 2}),
        }


class SchoolResourceForm(forms.ModelForm):
    class Meta:
        model = SchoolResource
        fields = ["resource_name", "status", "quantity", "last_updated_note", "details"]
