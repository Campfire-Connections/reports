# reports/utils.py

import pandas as pd
from django.core.files.base import ContentFile
from io import BytesIO


def generate_report_output(report, filters):
    """
    Generates a report using the report's query and filters.
    """
    # Mock example: Use pandas for data processing
    data = pd.DataFrame(
        [{"name": "Example", "value": 42}]
    )  # Replace with actual DB query
    output = BytesIO()
    data.to_csv(output, index=False)
    output_file = ContentFile(output.getvalue(), f"{report.name}.csv")
    return output_file
