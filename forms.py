# reports/forms.py

from django import forms
from .models import ReportTemplate


class ReportGenerationForm(forms.Form):
    report_template = forms.ModelChoiceField(
        queryset=ReportTemplate.objects.all(), label="Select Report"
    )
    filters = forms.JSONField(
        widget=forms.Textarea, label="Filters (JSON)", required=False
    )
