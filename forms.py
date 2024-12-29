# reports/forms.py

from django import forms
from .models import ReportTemplate


class ReportTemplateForm(forms.ModelForm):
    class Meta:
        model = ReportTemplate
        fields = ["name", "description", "filters", "query", "output_formats"]

        widgets = {
            "filters": forms.Textarea(attrs={"rows": 3}),
            "query": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            # Customize form for user-specific options if needed
            self.fields["output_formats"].widget.attrs[
                "placeholder"
            ] = "csv, pdf, excel"


class ReportGenerationForm(forms.Form):
    filters = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text="JSON-encoded filters to apply to the report",
    )
    output_format = forms.ChoiceField(
        choices=[("csv", "CSV"), ("pdf", "PDF"), ("excel", "Excel")], required=True
    )
