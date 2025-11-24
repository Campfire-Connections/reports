# reports/views.py

import json

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    FormView,
    ListView,
    UpdateView,
    TemplateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
import csv

from .forms import ReportGenerationForm, ReportTemplateForm
from .models import GeneratedReport, ReportTemplate
from .utils import generate_report_output
from .report_registry import available_reports_for, get_report


class ReportAccessMixin:
    """
    Mixin to check if the user has access to the report.
    """

    def has_report_access(self, report):
        return report.is_accessible_by(self.request.user)

    def get_object(self, queryset=None):
        report = super().get_object(queryset)
        if not self.has_report_access(report):
            raise PermissionDenied("You do not have access to this report.")
        return report


class ListReportsView(LoginRequiredMixin, ListView):
    """
    Displays a list of all reports accessible to the logged-in user.
    """

    model = ReportTemplate
    template_name = "reports/list_reports.html"
    context_object_name = "reports"

    def get_queryset(self):
        user = self.request.user
        return (
            ReportTemplate.objects.filter(
                Q(created_by=user) | Q(available_to=user)
            )
            .distinct()
            .select_related("created_by")
            .prefetch_related("available_to")
        )


class CreateReportTemplateView(LoginRequiredMixin, CreateView):
    """
    Allows users to create a new report template.
    """

    model = ReportTemplate
    form_class = ReportTemplateForm
    template_name = "reports/report_template_form.html"
    success_url = reverse_lazy("reports:list_user_reports")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user  # Pass the user to the form
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create A Report"
        return context

class UpdateReportTemplateView(LoginRequiredMixin, ReportAccessMixin, UpdateView):
    """
    Allows users to edit an existing report template they created or have access to.
    """

    model = ReportTemplate
    form_class = ReportTemplateForm
    template_name = "reports/report_template_form.html"
    success_url = reverse_lazy("reports:list_user_reports")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user  # Pass the user to the form
        return kwargs


class GenerateReportView(LoginRequiredMixin, FormView):
    """
    Generates a report based on the template and filters provided by the user.
    """

    template_name = "reports/generate_report.html"
    form_class = ReportGenerationForm

    def dispatch(self, request, *args, **kwargs):
        self.report = get_object_or_404(ReportTemplate, id=self.kwargs["report_id"])
        if not self.report.is_accessible_by(request.user):
            return JsonResponse({"error": "Access denied"}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        filters_raw = form.cleaned_data.get("filters") or "{}"
        output_format = form.cleaned_data["output_format"]

        try:
            filters = json.loads(filters_raw)
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Filters must be valid JSON."}, status=400
            )

        try:
            output_file = generate_report_output(
                self.report, filters, output_format
            )
            generated = GeneratedReport.objects.create(
                name=self.report.name,
                template=self.report,
                generated_by=self.request.user,
                filters_applied=filters,
                output_file=output_file,
            )

            return JsonResponse(
                {
                    "message": "Report generated successfully",
                    "file_url": generated.output_file.url,
                }
            )
        except Exception as e:
            return JsonResponse(
                {"error": f"Error generating report: {str(e)}"}, status=500
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report"] = self.report
        return context


# Built-in registry driven reports
class BuiltinReportsIndexView(LoginRequiredMixin, TemplateView):
    template_name = "reports/builtin_index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reports"] = available_reports_for(self.request.user)
        return context


class BuiltinReportDetailView(LoginRequiredMixin, TemplateView):
    template_name = "reports/builtin_detail.html"

    def get_filters(self):
        params = self.request.GET
        return {
            "facility_slug": params.get("facility_slug") or None,
            "faction_slug": params.get("faction_slug") or None,
            "start": params.get("start") or None,
            "end": params.get("end") or None,
            "unscoped": params.get("unscoped") == "1",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = get_report(kwargs["slug"])
        filters = self.get_filters()
        rows = list(report.get_rows(self.request.user, filters))
        columns = [label for _, label in report.columns]
        table_rows = [[row.get(col) for col in columns] for row in rows]
        context.update(
            report=report,
            filters=filters,
            rows=rows,
            columns=columns,
            table_rows=table_rows,
        )
        return context


class BuiltinReportExportView(BuiltinReportDetailView):
    """
    Export the current report as CSV or Excel (tab-delimited).
    """

    def get(self, request, *args, **kwargs):
        report = get_report(kwargs["slug"])
        filters = self.get_filters()
        rows = report.get_rows(request.user, filters)
        fmt = kwargs.get("fmt", "csv").lower()
        response = HttpResponse(content_type="text/csv")
        delimiter = ","
        if fmt == "excel":
            delimiter = "\t"
            response["Content-Disposition"] = (
                f'attachment; filename="{report.slug}.xlsx"'
            )
        else:
            response["Content-Disposition"] = (
                f'attachment; filename="{report.slug}.csv"'
            )

        writer = csv.DictWriter(response, fieldnames=[label for _, label in report.columns], delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return response
