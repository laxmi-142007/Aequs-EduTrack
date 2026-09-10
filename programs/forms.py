from django import forms
from .models import NGO, Project, Program, EVClassSession, Scholarship, CSRGrant
from schools.models import School
from students.models import Student


class NGOForm(forms.ModelForm):
    class Meta:
        model = NGO
        fields = [
            "name",
            "code",
            "contact_person",
            "phone",
            "email",
            "focus_areas",
            "headquarters",
            "partner_schools",
            "is_active",
            "notes",
        ]
        widgets = {
            "partner_schools": forms.SelectMultiple(attrs={"class": "form-select-multi"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "code",
            "description",
            "ngo",
            "target_schools",
            "start_date",
            "end_date",
            "allocated_budget",
            "spent_budget",
            "lead_coordinator",
            "status",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "target_schools": forms.SelectMultiple(attrs={"class": "form-select-multi"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = [
            "title",
            "code",
            "category",
            "project",
            "ngo",
            "description",
            "location_name",
            "village_or_town",
            "taluk",
            "district",
            "state",
            "gps_coordinates",
            "participating_schools",
            "academic_year",
            "status",
        ]
        widgets = {
            "participating_schools": forms.SelectMultiple(attrs={"class": "form-select-multi"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure mandatory location fields have required=True
        self.fields["location_name"].required = True
        self.fields["village_or_town"].required = True
        self.fields["taluk"].required = True
        self.fields["district"].required = True


class EVClassSessionForm(forms.ModelForm):
    class Meta:
        model = EVClassSession
        fields = [
            "session_title",
            "session_code",
            "program",
            "ngo",
            "school",
            "grade_level",
            "topic",
            "curriculum_module",
            "learning_objectives",
            "session_date",
            "start_time",
            "end_time",
            "duration_minutes",
            "facilitator_name",
            "facilitator_contact",
            "venue_or_route",
            "materials_or_kits_used",
            "attendee_count",
            "pre_assessment_avg",
            "post_assessment_avg",
            "student_feedback",
            "status",
        ]
        widgets = {
            "session_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "learning_objectives": forms.Textarea(attrs={"rows": 2}),
            "materials_or_kits_used": forms.Textarea(attrs={"rows": 2}),
            "student_feedback": forms.Textarea(attrs={"rows": 2}),
        }


class ScholarshipForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = [
            "student",
            "category",
            "scheme_name",
            "application_number",
            "academic_year",
            "sanctioned_amount",
            "disbursed_amount",
            "disbursement_date",
            "status",
            "aadhaar_verified",
            "income_cert_verified",
            "bank_account_verified",
            "employee_code",
            "employee_name",
            "employee_department",
            "plant_location",
            "donor_sponsor",
            "remarks",
        ]
        widgets = {
            "disbursement_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 2}),
        }
