from django import forms

from .models import AcademicRecord, get_current_academic_year


class AcademicRecordForm(forms.ModelForm):

    CLASS_COURSE_CHOICES = [
        ("", "Select Class / Course"),

        # School
        ("Class 1", "Class 1"),
        ("Class 2", "Class 2"),
        ("Class 3", "Class 3"),
        ("Class 4", "Class 4"),
        ("Class 5", "Class 5"),
        ("Class 6", "Class 6"),
        ("Class 7", "Class 7"),
        ("Class 8", "Class 8"),
        ("Class 9", "Class 9"),
        ("Class 10", "Class 10"),
        ("Class 11", "Class 11"),
        ("Class 12", "Class 12"),

        # PU
        ("1st PU", "1st PU"),
        ("2nd PU", "2nd PU"),

        # BE
        ("BE 1st year", "BE 1st year"),
        ("BE 2nd year", "BE 2nd year"),
        ("BE 3rd year", "BE 3rd year"),
        ("BE 4th year", "BE 4th year"),

        # Diploma
        ("Diploma 1st year", "Diploma 1st year"),
        ("Diploma 2nd year", "Diploma 2nd year"),
        ("Diploma 3rd year", "Diploma 3rd year"),

        # ITI
        ("ITI 1st year", "ITI 1st year"),
        ("ITI 2nd year", "ITI 2nd year"),
        ("ITI 3rd year", "ITI 3rd year"),
    ]

    class_or_course = forms.ChoiceField(
        choices=CLASS_COURSE_CHOICES,
        required=True,
        label="Class / Course",
    )

    class Meta:
        model = AcademicRecord

        fields = [
            "student",
            "academic_year",
            "class_or_course",
            "marks_obtained",
            "total_marks",
            "percentage",
            "rank",
            "previous_class",
            "promotion_status",
            "transfer_school",
            "remarks",
        ]

        widgets = {
            "academic_year": forms.Select(),

            "marks_obtained": forms.NumberInput(
                attrs={"step": "0.01"}
            ),

            "total_marks": forms.NumberInput(
                attrs={"step": "0.01"}
            ),

            "percentage": forms.NumberInput(
                attrs={"step": "0.01"}
            ),

            "previous_class": forms.TextInput(),

            "promotion_status": forms.Select(
                choices=[
                    ("", "Select Promotion Status"),
                    ("Promoted", "Promoted"),
                    ("Conditional", "Conditional"),
                    ("Not Promoted", "Not Promoted"),
                ]
            ),

            "transfer_school": forms.TextInput(),

            "remarks": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # ================================================================
        # ACADEMIC YEAR DROPDOWN
        # ================================================================

        current_year = get_current_academic_year()

        start_year = int(current_year[:4])

        academic_years = []

        for year in range(start_year, start_year + 5):

            academic_year = (
                f"{year}-{str(year + 1)[-2:]}"
            )

            academic_years.append(
                (
                    academic_year,
                    academic_year,
                )
            )

        self.fields["academic_year"].choices = academic_years

        # Current academic year for new records
        if not self.instance.pk:
            self.initial["academic_year"] = current_year

        # ================================================================
        # AUTOMATIC CURRENT CLASS
        # ================================================================

        if (
            not self.instance.pk
            and self.data.get("student")
        ):
            try:
                student_id = self.data.get("student")

                from students.models import Student

                student = Student.objects.get(
                    pk=student_id
                )

                current_class = (
                    student.current_class
                )

                if current_class in dict(
                    self.CLASS_COURSE_CHOICES
                ):
                    self.initial["class_or_course"] = (
                        current_class
                    )

            except (
                Student.DoesNotExist,
                ValueError,
                TypeError,
            ):
                pass

        # When editing an existing academic record,
        # keep its saved class.
        elif self.instance.pk:

            self.initial["class_or_course"] = (
                self.instance.class_or_course
            )