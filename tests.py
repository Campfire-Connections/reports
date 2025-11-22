from types import SimpleNamespace
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from reports.models import GeneratedReport, ReportTemplate
from reports.utils import generate_report_output
from core.tests import mute_profile_signals


User = get_user_model()


class ReportTemplateTests(TestCase):
    def test_is_accessible_by_checks_membership(self):
        with mute_profile_signals():
            owner = User.objects.create_user(
                username="report.owner",
                password="pass1234",
                user_type=User.UserType.ADMIN,
            )
            collaborator = User.objects.create_user(
                username="report.viewer",
                password="pass1234",
                user_type=User.UserType.ADMIN,
            )
        template = ReportTemplate.objects.create(
            name="Roster Snapshot",
            created_by=owner,
        )
        template.available_to.add(collaborator)

        with mute_profile_signals():
            stranger = User.objects.create_user(
                username="report.stranger",
                password="pass1234",
                user_type=User.UserType.ADMIN,
            )

        self.assertTrue(template.is_accessible_by(owner))
        self.assertTrue(template.is_accessible_by(collaborator))
        self.assertFalse(template.is_accessible_by(stranger))


class ListReportsViewTests(TestCase):
    def setUp(self):
        with mute_profile_signals():
            self.owner = User.objects.create_user(
                username="owner",
                password="pass12345",
                user_type=User.UserType.ADMIN,
            )
            self.viewer = User.objects.create_user(
                username="viewer",
                password="pass12345",
                user_type=User.UserType.ADMIN,
            )

        self.owned_report = ReportTemplate.objects.create(
            name="Owner Report",
            created_by=self.owner,
        )
        self.shared_report = ReportTemplate.objects.create(
            name="Shared Report",
            created_by=self.viewer,
        )
        self.shared_report.available_to.add(self.owner)

    def test_list_view_combines_owned_and_shared_reports(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("reports:list_user_reports"))
        self.assertEqual(response.status_code, 200)

        reports = list(response.context["reports"])
        self.assertEqual(len(reports), 2)
        names = {report.name for report in reports}
        self.assertIn("Owner Report", names)
        self.assertIn("Shared Report", names)


class GenerateReportViewTests(TestCase):
    def setUp(self):
        with mute_profile_signals():
            self.owner = User.objects.create_user(
                username="owner",
                password="pass12345",
                user_type=User.UserType.ADMIN,
            )
            self.other = User.objects.create_user(
                username="other",
                password="pass12345",
                user_type=User.UserType.ADMIN,
            )
        self.template = ReportTemplate.objects.create(
            name="Weekly Summary",
            created_by=self.owner,
        )
        self.url = reverse("reports:generate_report", args=[self.template.id])

    def test_generate_report_denies_unshared_template(self):
        self.client.force_login(self.other)
        response = self.client.post(
            self.url,
            {"filters": "{}", "output_format": "csv"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 403)

    def test_generate_report_success_returns_file_url(self):
        self.client.force_login(self.owner)
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_dir)
        with override_settings(MEDIA_ROOT=temp_dir):
            with patch(
                "reports.views.generate_report_output",
                return_value=ContentFile(b"rows", name="weekly.csv"),
            ) as mocked:
                response = self.client.post(
                    self.url,
                    {"filters": "{}", "output_format": "csv"},
                    HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["message"], "Report generated successfully"
        )
        self.assertTrue(payload["file_url"].endswith("weekly.csv"))
        self.assertEqual(GeneratedReport.objects.count(), 1)
        mocked.assert_called_once()


class GenerateReportOutputTests(TestCase):
    def setUp(self):
        self.report = SimpleNamespace(name="My Report")

    def test_csv_format_is_default(self):
        file_obj = generate_report_output(self.report, {}, "csv")
        self.assertTrue(file_obj.name.endswith(".csv"))
        self.assertIn(b"name,value", file_obj.read())

    def test_pdf_format_writes_lines(self):
        file_obj = generate_report_output(self.report, {}, "pdf")
        self.assertTrue(file_obj.name.endswith(".pdf"))
        content = file_obj.read()
        self.assertIn(b"Campfire Connections Report", content)

    def test_invalid_format_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_report_output(self.report, {}, "markdown")
