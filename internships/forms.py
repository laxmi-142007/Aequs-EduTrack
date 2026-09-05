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
                "accept": ".pdf,.jpg,.jpeg,.png",
            }
        ),
    )

    class Meta:
        model = InternshipDocument
        fields = [
            "document_type",
            "document",
        ]

    def clean_document(self):
        uploaded_file = self.cleaned_data.get("document")

        if not uploaded_file:
            raise forms.ValidationError(
                "Please select a document."
            )

        allowed_extensions = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
        ]

        filename = uploaded_file.name.lower()

        if not any(
            filename.endswith(extension)
            for extension in allowed_extensions
        ):
            raise forms.ValidationError(
                "Only PDF, JPG, JPEG and PNG files "
                "are allowed."
            )

        return uploaded_file
