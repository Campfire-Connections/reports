# reports/report_registry.py
"""
Lightweight registry for built-in reports that auto-scope to the viewer.
"""
from typing import List, Dict, Any, Iterable, Tuple
from django.http import Http404
from django.utils import timezone

from enrollment.models.faction import FactionEnrollment
from reports.utils import (
    get_user_scope_filters,
    user_can_unscope,
    queryset_to_rows,
)


class BaseReport:
    slug: str = ""
    name: str = ""
    description: str = ""
    allow_unscoped: bool = False
    columns: List[Tuple[str, str]] = []

    def is_available_to(self, user) -> bool:
        return bool(user and user.is_authenticated)

    def apply_scope(self, qs, user, filters: Dict[str, Any]):
        if self.allow_unscoped and user_can_unscope(user) and filters.get("unscoped"):
            return qs
        scope_filters = get_user_scope_filters(user, target="faction")
        if scope_filters:
            qs = qs.filter(**scope_filters)
        return qs

    def get_queryset(self, user, filters: Dict[str, Any]):
        raise NotImplementedError

    def get_rows(self, user, filters: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        qs = self.get_queryset(user, filters)
        qs = self.apply_scope(qs, user, filters)
        return queryset_to_rows(qs, self.columns)


class FactionEnrollmentReport(BaseReport):
    slug = "faction-enrollments"
    name = "Faction Enrollments"
    description = "Enrollments by faction, week, and facility with quarters and dates."
    columns = [
        ("faction__name", "Faction"),
        ("week__facility_enrollment__facility__name", "Facility"),
        ("week__name", "Week"),
        ("quarters__name", "Quarters"),
        ("start", "Start"),
        ("end", "End"),
    ]

    def get_queryset(self, user, filters: Dict[str, Any]):
        qs = FactionEnrollment.objects.select_related(
            "faction",
            "week",
            "week__facility_enrollment__facility",
            "quarters",
        )
        faction_slug = filters.get("faction_slug")
        facility_slug = filters.get("facility_slug")
        start = filters.get("start")
        end = filters.get("end")

        if faction_slug:
            qs = qs.filter(faction__slug=faction_slug)
        if facility_slug:
            qs = qs.filter(week__facility_enrollment__facility__slug=facility_slug)
        if start:
            qs = qs.filter(start__gte=start)
        if end:
            qs = qs.filter(end__lte=end)
        return qs


REPORTS: List[BaseReport] = [
    FactionEnrollmentReport(),
]


def available_reports_for(user) -> List[BaseReport]:
    return [r for r in REPORTS if r.is_available_to(user)]


def get_report(slug: str) -> BaseReport:
    for report in REPORTS:
        if report.slug == slug:
            return report
    raise Http404("Report not found")
