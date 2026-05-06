from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from workflows.models import WorkflowDefinition, WorkflowStep, WorkflowRun
from workflows.services import WorkflowService


class WorkflowViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            password="testpass123",
        )

        self.other_user = User.objects.create_user(
            username="someone.else",
            password="testpass123",
        )

        self.workflow = WorkflowDefinition.objects.create(
            key="purchase_approval",
            name="Purchase Approval",
            description="Approval workflow",
            is_active=True,
        )

        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Manager Approval",
            order=1,
            assigned_role="manager",
        )

        WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Finance Approval",
            order=2,
            assigned_role="finance",
        )

        self.run = WorkflowService.start_workflow(
            workflow_key="purchase_approval",
            started_by="admin",
            reference="PO-2001",
        )

    def test_run_detail_page_loads(self):
        response = self.client.get(
            reverse("workflow-run-detail", kwargs={"reference": self.run.reference})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PO-2001")
        self.assertContains(response, "Purchase Approval")
        self.assertContains(response, "Manager Approval")
    
    def test_assigned_user_can_submit_decision(self):
        self.client.login(username="admin", password="testpass123")

        response = self.client.post(
            reverse("workflow-run-detail", kwargs={"reference": self.run.reference}),
            {
                "outcome": "approved",
                "comment": "Looks good",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.run.refresh_from_db()
        first_step = self.run.step_runs.get(step__order=1)
        second_step = self.run.step_runs.get(step__order=2)

        self.assertEqual(first_step.status, "completed")
        self.assertEqual(second_step.status, "in_progress")

    def test_unassigned_user_cannot_submit_decision(self):
        User.objects.create_user(username="someone_else", password="testpass123")
        self.client.login(username="someone_else", password="testpass123")

        response = self.client.post(
            reverse("workflow-run-detail", kwargs={"reference": self.run.reference}),
            {
                "outcome": "approved",
                "comment": "Trying to approve",
            },
        )

        self.assertEqual(response.status_code, 403)

        first_step = self.run.step_runs.get(step__order=1)
        second_step = self.run.step_runs.get(step__order=2)

        self.assertEqual(first_step.status, "in_progress")
        self.assertEqual(second_step.status, "pending")