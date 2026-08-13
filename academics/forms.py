from django import forms
from .models import AcademicRecord


class AcademicRecordForm(forms.ModelForm):
    class Meta:
        model = AcademicRecord
        fields = [
            "student",
            "academic_year",
            "class_or_course",
            "percentage",
            "marks_obtained",
            "total_marks",
            "rank",
            "promotion_status",
            "transfer_school",
            "remarks",
        ]
        widgets = {
            "remarks": forms.Textarea(attrs={"rows": 2}),
        }
