# reports/tables.py

import django_tables2 as tables

from core.tables.base import BaseTable

from .models import GeneratedReport


class GeneratedReportTable(BaseTable):
    class Meta:
        model = GeneratedReport
        template_name = "django_tables2/bootstrap5.html"
        fields = ["name", "template", "generated_by", "created_at", "output_file"]
        order_by = "-created_at"
