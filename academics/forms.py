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

    class Meta:
        model = AcademicRecord
        fields = "__all__"

        widgets = {
            "marks_obtained": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "total_marks": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "percentage": forms.NumberInput(
                attrs={
                    "readonly": "readonly",
                    "step": "0.01",
                }
            ),
            "rank": forms.NumberInput(
                attrs={
                    "readonly": "readonly",
                }
            ),
            "previous_class": forms.TextInput(
                attrs={
                    "readonly": "readonly",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        student_id = self.initial.get("student")

        if self.instance and self.instance.pk:
            student_id = self.instance.student_id

        # When editing/creating with a student already selected,
        # show the previous academic class.
        if student_id:
            previous = (
                AcademicRecord.objects
                .filter(student_id=student_id)
                .exclude(
                    pk=self.instance.pk
                    if self.instance.pk
                    else None
                )
                .order_by("-academic_year", "-id")
                .first()
            )

            if previous:
                self.initial["previous_class"] = (
                    previous.class_or_course
                )
