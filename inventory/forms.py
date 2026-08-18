from django import forms

from .models import Laptop, LaptopAssignment


class LaptopForm(forms.ModelForm):

    class Meta:
        model = Laptop

        fields = [
            "asset_number",
            "serial_number",
            "brand",
            "model_name",
            "purchase_date",
            "purchase_cost",
            "condition",
            "status",
            "warranty_expiry",
            "notes",
        ]

        widgets = {
            "asset_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "serial_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "brand": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "model_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "purchase_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "purchase_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
            "condition": forms.Select(
                attrs={"class": "form-control"}
            ),
            "status": forms.Select(
                attrs={"class": "form-control"}
            ),
            "warranty_expiry": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }


class LaptopIssueForm(forms.Form):

    student = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
    )

    laptop = forms.ModelChoiceField(
        queryset=Laptop.objects.filter(
            status=Laptop.Status.AVAILABLE
        ).order_by("asset_number"),
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
    )

    academic_year = forms.CharField(
        max_length=20,
        initial="2026-27",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: 2026-27",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        from students.models import Student

        super().__init__(*args, **kwargs)

        self.fields["student"].queryset = Student.objects.all().order_by(
            "student_name"
        )


class LaptopReturnForm(forms.Form):

    assignment = forms.ModelChoiceField(
        queryset=LaptopAssignment.objects.filter(
            status=LaptopAssignment.Status.ISSUED
        ).select_related(
            "student",
            "laptop",
        ),
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
    )

    return_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional return notes",
            }
        ),
    )


class LaptopReplaceForm(forms.Form):

    assignment = forms.ModelChoiceField(
        queryset=LaptopAssignment.objects.filter(
            status=LaptopAssignment.Status.ISSUED
        ).select_related(
            "student",
            "laptop",
        ),
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
    )

    replacement_laptop = forms.ModelChoiceField(
        queryset=Laptop.objects.filter(
            status=Laptop.Status.AVAILABLE
        ).order_by("asset_number"),
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
    )

    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Reason for replacement",
            }
        ),
    )
