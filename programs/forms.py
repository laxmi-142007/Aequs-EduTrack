from django import forms
from .models import NGO, Project, Program, EVClassSession, Scholarship, CSRGrant, Location, MentorshipSession
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
    programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select-multi", "size": "4"}),
        help_text="Select operational sub-programs to link under this project",
    )

    class Meta:
        model = Project
        fields = [
            "name",
            "code",
            "description",
            "ngo",
            "locations",
            "target_schools",
            "start_date",
            "end_date",
            "allocated_budget",
            "spent_budget",
            "lead_coordinator",
            "status",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"placeholder": "Auto-generated (e.g. PRJ-2026-001) or enter custom code"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "locations": forms.SelectMultiple(attrs={"class": "form-select-multi", "size": "4"}),
            "target_schools": forms.SelectMultiple(attrs={"class": "form-select-multi", "size": "4"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].required = False
        if not self.instance.pk and not self.initial.get("code"):
            self.initial["code"] = Project.generate_next_code()
        self.fields["locations"].queryset = Location.objects.filter(is_active=True).order_by("district", "name")
        self.fields["programs"].queryset = Program.objects.filter(is_archived=False).order_by("title")
        if self.instance and self.instance.pk:
            self.initial["programs"] = list(self.instance.programs.values_list("pk", flat=True))

    def save(self, commit=True):
        project = super().save(commit=commit)
        if commit:
            selected_programs = self.cleaned_data.get("programs", [])
            # Dissociate programs no longer selected
            project.programs.exclude(pk__in=[p.pk for p in selected_programs]).update(project=None)
            # Associate selected programs
            for prg in selected_programs:
                prg.project = project
                prg.save(update_fields=["project"])
        return project



class ProgramForm(forms.ModelForm):
    DISTRICT_CHOICES = [
        ("Belagavi", "Belagavi"),
        ("Hubli/Dharwad", "Hubli/Dharwad"),
        ("Koppal", "Koppal"),
    ]

    district = forms.MultipleChoiceField(
        choices=DISTRICT_CHOICES,
        widget=forms.SelectMultiple(attrs={"class": "form-select-multi", "size": "3"}),
        help_text="Select one or more districts",
        required=True,
    )

    class Meta:
        model = Program
        fields = [
            "title",
            "code",
            "category",
            "project",
            "ngo",
            "locations",
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
            "locations": forms.SelectMultiple(attrs={"class": "form-select-multi", "size": "4"}),
            "participating_schools": forms.SelectMultiple(attrs={"class": "form-select-multi"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(is_archived=False).order_by("name")
        self.fields["project"].empty_label = "-- Standalone Program (No Parent Project) --"
        self.fields["locations"].queryset = Location.objects.filter(is_active=True).order_by("district", "name")
        # Ensure mandatory location fields have required=True
        self.fields["location_name"].required = True
        self.fields["village_or_town"].required = True
        self.fields["taluk"].required = True
        self.fields["district"].required = True

        if self.instance and self.instance.pk and self.instance.district:
            selected = [d.strip() for d in self.instance.district.split(",") if d.strip()]
            self.initial["district"] = selected

    def clean_district(self):
        district_data = self.cleaned_data.get("district")
        if isinstance(district_data, (list, tuple)):
            return ", ".join(district_data)
        return district_data or ""


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
            "project",
            "program",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.filter(is_archived=False).order_by("name")
        self.fields["project"].empty_label = "-- Direct Foundation / Unlinked --"
        self.fields["program"].queryset = Program.objects.filter(is_archived=False).order_by("title")
        self.fields["program"].empty_label = "-- Standalone / No Program --"


class LocationForm(forms.ModelForm):
    DISTRICT_CHOICES = [
        ("Belagavi", "Belagavi"),
        ("Dharwad", "Dharwad"),
        ("Hubli/Dharwad", "Hubli/Dharwad"),
        ("Koppal", "Koppal"),
        ("Other", "Other"),
    ]

    district = forms.ChoiceField(
        choices=DISTRICT_CHOICES,
        required=True,
    )

    class Meta:
        model = Location
        fields = [
            "name",
            "code",
            "district",
            "taluk",
            "village_or_town",
            "state",
            "pincode",
            "address",
            "is_active",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "code": forms.TextInput(attrs={"placeholder": "e.g. LOC-BGV-01 (Auto-generated if left blank)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].required = False

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip()
        if not code:
            district = self.cleaned_data.get("district", "LOC")
            prefix = f"LOC-{district[:3].upper()}-"
            count = Location.objects.filter(code__startswith=prefix).count() + 1
            code = f"{prefix}{count:02d}"
            while Location.objects.filter(code=code).exists():
                count += 1
                code = f"{prefix}{count:02d}"
        return code


class MentorshipSessionForm(forms.ModelForm):
    class Meta:
        model = MentorshipSession
        fields = [
            "session_title",
            "session_code",
            "project",
            "program",
            "student",
            "mentor_name",
            "mentor_email",
            "mentor_designation",
            "session_date",
            "duration_minutes",
            "topic",
            "notes",
            "feedback",
            "status",
        ]
        widgets = {
            "session_date": forms.DateInput(attrs={"type": "date"}),
            "session_code": forms.TextInput(attrs={"placeholder": "Auto-generated (e.g. MNT-2026-001)"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "feedback": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["session_code"].required = False
        self.fields["project"].queryset = Project.objects.filter(is_archived=False).order_by("name")
        self.fields["project"].empty_label = "-- Unlinked / Direct Mentorship --"
        self.fields["program"].queryset = Program.objects.filter(is_archived=False).order_by("title")
        self.fields["program"].empty_label = "-- No Program Assigned --"

