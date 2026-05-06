from django.test import TestCase

from workflows.models import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowRun,
    WorkflowStepRun,
    WorkflowDecision,
)
from workflows.services import WorkflowService


class WorkflowServiceTests(TestCase):
    def setUp(self):
        self.workflow = WorkflowDefinition.objects.create(
            key="purchase_approval",
            name="Purchase Approval",
            description="Approval workflow",
            is_active=True,
        )

        self.manager_step = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Manager Approval",
            order=1,
            assigned_role="manager",
        )

        self.finance_step = WorkflowStep.objects.create(
            workflow=self.workflow,
            name="Finance Approval",
            order=2,
            assigned_role="finance",
        )

    def test_start_workflow_creates_run_and_activates_first_step(self):
        run = WorkflowService.start_workflow(
            workflow_key="purchase_approval",
            started_by="admin",
            reference="PO-1001",
        )

        self.assertEqual(run.reference, "PO-1001")
        self.assertEqual(run.status, WorkflowRun.Status.PENDING)

        steps = WorkflowStepRun.objects.filter(workflow_run=run).order_by("step__order")
        self.assertEqual(steps.count(), 2)

        first_step = steps[0]
        second_step = steps[1]

        self.assertEqual(first_step.status, WorkflowStepRun.Status.IN_PROGRESS)
        self.assertEqual(first_step.assigned_to, "admin")

        self.assertEqual(second_step.status, WorkflowStepRun.Status.PENDING)
    
    def test_approved_decision_moves_to_next_step(self):
        run = WorkflowService.start_workflow(
            workflow_key="purchase_approval",
            started_by="admin",
            reference="PO-1002",
        )

        first_step = run.step_runs.get(step__order=1)

        WorkflowService.record_decision(
            step_run_id=first_step.id,
            outcome=WorkflowDecision.Outcome.APPROVED,
            decided_by="admin",
            comment="Approved by manager",
        )

        first_step.refresh_from_db()
        second_step = run.step_runs.get(step__order=2)
        run.refresh_from_db()

        self.assertEqual(first_step.status, WorkflowStepRun.Status.COMPLETED)
        self.assertEqual(second_step.status, WorkflowStepRun.Status.IN_PROGRESS)
        self.assertEqual(second_step.assigned_to, "finance.user")
        self.assertEqual(run.status, WorkflowRun.Status.PENDING)

    def test_rejected_decision_completes_workflow(self):
        run = WorkflowService.start_workflow(
            workflow_key="purchase_approval",
            started_by="admin",
            reference="PO-1003",
        )

        first_step = run.step_runs.get(step__order=1)

        WorkflowService.record_decision(
            step_run_id=first_step.id,
            outcome=WorkflowDecision.Outcome.REJECTED,
            decided_by="admin",
            comment="Rejected by manager",
        )

        first_step.refresh_from_db()
        run.refresh_from_db()

        self.assertEqual(first_step.status, WorkflowStepRun.Status.COMPLETED)
        self.assertEqual(run.status, WorkflowRun.Status.COMPLETED)
        self.assertIsNotNone(run.completed_at)

    def test_sent_back_reopens_previous_step(self):
        run = WorkflowService.start_workflow(
            workflow_key="purchase_approval",
            started_by="admin",
            reference="PO-1004",
        )

        first_step = run.step_runs.get(step__order=1)

        WorkflowService.record_decision(
            step_run_id=first_step.id,
            outcome=WorkflowDecision.Outcome.APPROVED,
            decided_by="admin",
            comment="Approved by manager",
        )

        second_step = run.step_runs.get(step__order=2)

        WorkflowService.record_decision(
            step_run_id=second_step.id,
            outcome=WorkflowDecision.Outcome.SENT_BACK,
            decided_by="finance.user",
            comment="Need manager to review again",
        )

        first_step.refresh_from_db()
        second_step.refresh_from_db()
        run.refresh_from_db()

        self.assertEqual(first_step.status, WorkflowStepRun.Status.IN_PROGRESS)
        self.assertEqual(first_step.assigned_to, "admin")

        self.assertEqual(second_step.status, WorkflowStepRun.Status.PENDING)
        self.assertEqual(run.status, WorkflowRun.Status.PENDING)

    def test_cannot_decide_same_step_twice(self):
        run = WorkflowService.start_workflow(
            workflow_key="purchase_approval",
            started_by="admin",
            reference="PO-1005",
        )

        first_step = run.step_runs.get(step__order=1)

        WorkflowService.record_decision(
            step_run_id=first_step.id,
            outcome=WorkflowDecision.Outcome.APPROVED,
            decided_by="admin",
            comment="Approved once",
        )

        with self.assertRaises(ValueError):
            WorkflowService.record_decision(
                step_run_id=first_step.id,
                outcome=WorkflowDecision.Outcome.APPROVED,
                decided_by="admin",
                comment="Approved twice",
            )