from django import forms

from .models import InternshipDocument


class InternshipDocumentForm(forms.ModelForm):
    """
    Form for uploading internship documents.

    The document_type choices are taken directly from
    InternshipDocument.DocumentType so that the dropdown
    always contains the choices defined in models.py.
    """

    document_type = forms.ChoiceField(
        label="Document Type",
        required=True,
        choices=InternshipDocument.DocumentType.choices,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    document = forms.FileField(
        label="Select Document",
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    class Meta:
        model = InternshipDocument
        fields = [
            "document_type",
            "document",
        ]
