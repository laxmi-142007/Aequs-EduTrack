from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Report

User = get_user_model()


class ReportForm(forms.ModelForm):
    allowed_roles = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "role-cb"}),
        help_text="Select which system roles can view this report",
    )
    status = forms.ChoiceField(
        choices=Report.Status.choices,
        required=False,
        initial=Report.Status.PUBLISHED,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    row_limit = forms.IntegerField(
        required=False,
        initial=100,
        min_value=0,
        max_value=10000,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 100 (0 for all matching records)"}),
    )

    class Meta:
        model = Report
        fields = [
            "title",
            "report_type",
            "status",
            "description",
            "summary_notes",
            "attachment",
            "row_limit",
            "academic_year",
            "category_filter",
            "date_from",
            "date_to",
            "visibility",
            "allowed_roles",
            "allowed_groups",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Q3 Belagavi Laptop Distribution Summary"}),
            "report_type": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Purpose, methodology, or audience for this report..."}),
            "summary_notes": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Executive summary, key audit findings, observations, or recommendations..."}),
            "attachment": forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.docx,.xlsx,.csv,.png,.jpg,.jpeg", "id": "id_attachment"}),
            "academic_year": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 2024-2025 (or blank for all)"}),
            "category_filter": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. LAPTOP or Belagavi (optional)"}),
            "date_from": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "date_to": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "visibility": forms.Select(attrs={"class": "form-control", "id": "id_visibility"}),
            "allowed_groups": forms.SelectMultiple(attrs={"class": "form-control", "size": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically load all role choices
        if hasattr(User, "get_all_role_choices"):
            self.fields["allowed_roles"].choices = User.get_all_role_choices()
        else:
            self.fields["allowed_roles"].choices = getattr(User, "Role", {}).choices

        # Populate initial allowed_roles from comma-separated string if instance exists
        if self.instance and self.instance.pk and self.instance.allowed_roles:
            self.initial["allowed_roles"] = [
                r.strip() for r in self.instance.allowed_roles.split(",") if r.strip()
            ]

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if attachment and hasattr(attachment, "size"):
            # Max 25 MB
            if attachment.size > 25 * 1024 * 1024:
                raise forms.ValidationError("File size exceeds 25 MB limit.")
        return attachment

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("status"):
            cleaned_data["status"] = Report.Status.PUBLISHED
        if cleaned_data.get("row_limit") is None:
            cleaned_data["row_limit"] = 100
        visibility = cleaned_data.get("visibility")
        roles = cleaned_data.get("allowed_roles")
        groups = cleaned_data.get("allowed_groups")

        if visibility == Report.Visibility.ROLES and not roles:
            self.add_error("allowed_roles", "Please select at least one role when visibility is set to 'Specific System Roles'.")

        if visibility == Report.Visibility.GROUPS and not groups:
            self.add_error("allowed_groups", "Please select at least one group when visibility is set to 'Specific User Groups'.")

        return cleaned_data

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        roles = self.cleaned_data.get("allowed_roles", [])
        instance.allowed_roles = ",".join(roles) if roles else ""

        if self.data.get("clear_attachment") == "1":
            if instance.attachment:
                instance.attachment.delete(save=False)
            instance.attachment = None

        if user and not instance.created_by:
            instance.created_by = user

        if commit:
            instance.save()
            self.save_m2m()

        return instance
