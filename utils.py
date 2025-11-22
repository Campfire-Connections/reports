# reports/utils.py

import csv
from io import StringIO
from typing import Iterable, Mapping

from django.core.files.base import ContentFile
from django.utils.text import slugify


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
