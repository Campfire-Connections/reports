# reports/views.py

import json

from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, FormView
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import ReportTemplate, GeneratedReport
from .forms import ReportTemplateForm, ReportGenerationForm
from .utils import generate_report_output


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
        return ReportTemplate.objects.filter(
            available_to=user
        ) | ReportTemplate.objects.filter(created_by=user)


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
        filters = form.cleaned_data.get("filters", "{}")
        output_format = form.cleaned_data["output_format"]

        try:
            filters = json.loads(filters)
            output_file = generate_report_output(self.report, filters, output_format)

            GeneratedReport.objects.create(
                name=self.report.name,
                template=self.report,
                generated_by=self.request.user,
                filters_applied=filters,
                output_file=output_file,
            )

            return JsonResponse(
                {
                    "message": "Report generated successfully",
                    "file_url": output_file.url,
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
