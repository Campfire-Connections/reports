# reports/utils.py

import csv
from io import StringIO
from typing import Iterable, Mapping, Sequence, Tuple, Dict, Any

from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify
from django.core.files.base import ContentFile
from core.utils import (
    get_leader_profile,
    get_faculty_profile,
    is_leader_admin,
    is_faculty_admin,
    is_department_admin,
)
from user.models import User


def _serialize_rows(rows: Iterable[Mapping], delimiter=",") -> bytes:
    buffer = StringIO()
    rows = list(rows)
    if not rows:
        return b""
    writer = csv.DictWriter(
        buffer, fieldnames=list(rows[0].keys()), delimiter=delimiter
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def _pdf_placeholder(rows: Iterable[Mapping]) -> bytes:
    buffer = StringIO()
    buffer.write("Campfire Connections Report\n")
    for row in rows:
        line = ", ".join(f"{key}={value}" for key, value in row.items())
        buffer.write(f"{line}\n")
    return buffer.getvalue().encode("utf-8")


def generate_report_output(report, filters=None, output_format="csv"):
    """
    Generates a lightweight file for the requested report.

    This helper is intentionally simple but provides consistent filenames and
    format-specific encoders so unit tests and future exporters can rely on it.
    """

    default_rows = [{"name": report.name, "value": 1}]
    rows = default_rows
    if isinstance(filters, dict):
        rows = filters.get("rows") or default_rows

    output_format = (output_format or "csv").lower()
    if output_format == "pdf":
        payload = _pdf_placeholder(rows)
        extension = "pdf"
    elif output_format == "excel":
        payload = _serialize_rows(rows, delimiter="\t")
        extension = "xlsx"
    elif output_format == "csv":
        payload = _serialize_rows(rows)
        extension = "csv"
    else:
        raise ValueError(f"Unsupported format: {output_format}")

    filename = f"{slugify(report.name) or 'report'}.{extension}"
    return ContentFile(payload, name=filename)


def queryset_to_rows(qs, columns: Sequence[Tuple[str, str]]) -> Iterable[Mapping[str, Any]]:
    """
    Convert a queryset to dictionaries using dotted lookups defined by columns.
    columns: list of tuples (field_path, label)
    """
    for obj in qs:
        row = {}
        for field_path, label in columns:
            value = _get_nested_attr(obj, field_path)
            row[label] = value
        yield row


def _get_nested_attr(obj, attr_path, default=None):
    try:
        for part in attr_path.split("__"):
            obj = getattr(obj, part)
            if callable(obj):
                obj = obj()
        return obj
    except AttributeError:
        return default


def get_user_scope_filters(user: User, *, target: str = "faction") -> Dict[str, Any]:
    """
    Build queryset filters based on the current user's scope.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return {}

    # Superusers/staff are unscoped by default
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return {}

    # Leader: scope to their faction
    leader_profile = get_leader_profile(user)
    if leader_profile and leader_profile.faction_id:
        return {"faction": leader_profile.faction}

    # Faculty: scope to their facility
    faculty_profile = get_faculty_profile(user)
    if faculty_profile and faculty_profile.facility_id:
        facility = getattr(faculty_profile, "facility", None)
        if target == "facility":
            return {"facility": facility}
        return {"week__facility_enrollment__facility": facility}

    # Attendee: scope to faction if present
    attendee_profile = getattr(user, "attendeeprofile_profile", None)
    if attendee_profile and getattr(attendee_profile, "faction_id", None):
        return {"faction": attendee_profile.faction}

    # Organization fallback
    try:
        org = user.get_profile().organization
    except Exception:
        org = None
    if org:
        if target == "facility":
            return {"organization": org}
        return {"faction__organization": org}
    return {}


def user_can_unscope(user: User) -> bool:
    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_staff", False)
        or is_leader_admin(user)
        or is_faculty_admin(user)
        or is_department_admin(user)
    )
