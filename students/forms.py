from django import forms

from .models import Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "admission_number",
            "student_name",
            "date_of_birth",
            "gender",
            "photo",
            "school",
            "current_class",
            "section",
            "roll_number",
            "parent_name",
            "parent_phone",
            "parent_email",
            "relationship_to_student",
            "student_phone",
            "email",
            "address",
            "status",
            "admission_date",
        ]

        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date"}
            ),
            "admission_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "address": forms.Textarea(
                attrs={"rows": 3}
            ),
        }