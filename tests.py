from django.test import TestCase

from django.contrib.auth import get_user_model

from reports.models import ReportTemplate


User = get_user_model()


class ReportTemplateTests(TestCase):
    def test_is_accessible_by_checks_membership(self):
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

        self.assertTrue(template.is_accessible_by(owner))
        self.assertTrue(template.is_accessible_by(collaborator))
