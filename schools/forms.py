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
            "address": forms.Textarea(attrs={"rows": 3}),
            "established_date": forms.DateInput(attrs={"type": "date"}),
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