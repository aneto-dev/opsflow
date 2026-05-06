from django.core.management.base import BaseCommand
from workflows.models import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowRun,
    WorkflowStepRun,
    WorkflowDecision,
)
from workflows.services import WorkflowService


class Command(BaseCommand):
    help = "Seed clean demo workflow data for local development"

    def handle(self, *args, **kwargs):
        self.stdout.write("Resetting demo workflow data...")

        WorkflowDecision.objects.all().delete()
        WorkflowStepRun.objects.all().delete()
        WorkflowRun.objects.all().delete()
        WorkflowStep.objects.all().delete()
        WorkflowDefinition.objects.all().delete()

        workflow = WorkflowDefinition.objects.create(
            key="purchase_approval",
            name="Purchase Approval",
            is_active=True,
        )

        WorkflowStep.objects.create(
            workflow=workflow,
            name="Manager Approval",
            order=1,
            assigned_role="manager",
            is_required=True,
        )

        WorkflowStep.objects.create(
            workflow=workflow,
            name="Finance Approval",
            order=2,
            assigned_role="finance",
            is_required=True,
        )

        # PO-1001 Completed
        run1 = WorkflowService.start_workflow("purchase_approval", "aires", "PO-1001")
        WorkflowService.record_decision(
            step_run_id=run1.step_runs.get(step__order=1).id,
            outcome="approved",
            decided_by="aires",
            comment="Approved by manager",
        )
        WorkflowService.record_decision(
            step_run_id=run1.step_runs.get(step__order=2).id,
            outcome="approved",
            decided_by="finance.user",
            comment="Approved by finance",
        )

        # PO-1002 Rejected
        run2 = WorkflowService.start_workflow("purchase_approval", "aires", "PO-1002")
        WorkflowService.record_decision(
            step_run_id=run2.step_runs.get(step__order=1).id,
            outcome="rejected",
            decided_by="aires",
            comment="Rejected by manager",
        )

        # PO-1003 Pending
        WorkflowService.start_workflow("purchase_approval", "aires", "PO-1003")

        # PO-1004 Sent Back
        run4 = WorkflowService.start_workflow("purchase_approval", "admin", "PO-1004")
        WorkflowService.record_decision(
            step_run_id=run4.step_runs.get(step__order=1).id,
            outcome="approved",
            decided_by="admin",
            comment="Approved by manager",
        )
        WorkflowService.record_decision(
            step_run_id=run4.step_runs.get(step__order=2).id,
            outcome="sent_back",
            decided_by="finance.user",
            comment="Need more detail before approval",
        )

        # PO-1005 Escalated
        run5 = WorkflowService.start_workflow("purchase_approval", "admin", "PO-1005")
        WorkflowService.record_decision(
            step_run_id=run5.step_runs.get(step__order=1).id,
            outcome="approved",
            decided_by="admin",
            comment="Approved by manager",
        )
        WorkflowService.record_decision(
            step_run_id=run5.step_runs.get(step__order=2).id,
            outcome="escalated",
            decided_by="finance.user",
            comment="Escalating to senior finance",
        )

        self.stdout.write(self.style.SUCCESS("Demo workflow data seeded successfully."))