# reports/views.py

import json
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from .models import ReportTemplate, GeneratedReport
from .forms import ReportGenerationForm
from .utils import generate_report_output  # Utility function for processing data


@login_required
@permission_required("reports.can_view_reports", raise_exception=True)
def list_reports(request):
    reports = ReportTemplate.objects.all()
    return render(request, "reports/list_reports.html", {"reports": reports})


@login_required
@permission_required("reports.can_generate_report", raise_exception=True)
def generate_report(request, report_id):
    report = get_object_or_404(ReportTemplate, id=report_id)
    form = ReportGenerationForm(request.POST or None)
    if form.is_valid():
        filters = json.loads(form.cleaned_data["filters"])
        output_file = generate_report_output(report, filters)

        GeneratedReport.objects.create(
            name=report.name,
            template=report,
            generated_by=request.user,
            filters_applied=filters,
            output_file=output_file,
        )

        return JsonResponse(
            {"message": "Report generated successfully", "file": output_file.url}
        )
    return render(
        request, "reports/generate_report.html", {"form": form, "report": report}
    )
