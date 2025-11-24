# reports/urls.py

from django.urls import path
from .views import (
    ListReportsView,
    CreateReportTemplateView,
    UpdateReportTemplateView,
    GenerateReportView,
    BuiltinReportsIndexView,
    BuiltinReportDetailView,
    BuiltinReportExportView,
)

app_name = "reports"

urlpatterns = [
    path("", ListReportsView.as_view(), name="list_user_reports"),
    path("builtin/", BuiltinReportsIndexView.as_view(), name="builtin_index"),
    path(
        "builtin/<slug:slug>/",
        BuiltinReportDetailView.as_view(),
        name="builtin_detail",
    ),
    path(
        "builtin/<slug:slug>/export/<str:fmt>/",
        BuiltinReportExportView.as_view(),
        name="builtin_export",
    ),
    path("create/", CreateReportTemplateView.as_view(), name="create_report_template"),
    path(
        "<int:pk>/edit/",
        UpdateReportTemplateView.as_view(),
        name="update_report_template",
    ),
    path(
        "<int:report_id>/generate/",
        GenerateReportView.as_view(),
        name="generate_report",
    ),
]
