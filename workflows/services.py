from django.db import transaction
from django.utils import timezone

from workflows.models import (
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStep,
    WorkflowStepRun,
    WorkflowDecision,
)

class WorkflowService:
    @staticmethod
    @transaction.atomic
    def start_workflow(workflow_key: str, started_by: str, reference: str) -> WorkflowRun:
        workflow = WorkflowDefinition.objects.get(key=workflow_key, is_active=True)

        workflow_run = WorkflowRun.objects.create(
            workflow=workflow,
            reference=reference,
            started_by=started_by,
        )

        WorkflowService._create_step_runs(workflow_run)
        WorkflowService._activate_next_step(workflow_run)

        return workflow_run
    
    @staticmethod
    def _create_step_runs(workflow_run: WorkflowRun) -> None:
        steps = WorkflowStep.objects.filter(workflow=workflow_run.workflow).order_by("order")

        for step in steps:
            WorkflowStepRun.objects.create(
                workflow_run=workflow_run,
                step=step,
                status=WorkflowStepRun.Status.PENDING,
                assigned_to=step.assigned_role,
            )
    
    @staticmethod
    def _activate_next_step(workflow_run: WorkflowRun) -> None:
        next_step = (
            WorkflowStepRun.objects
            .filter(
                workflow_run=workflow_run,
                status=WorkflowStepRun.Status.PENDING,
            )
            .order_by("step__order")
            .first()
        )

        if not next_step:
            WorkflowService._complete_workflow(workflow_run)
            return
        

        next_step.assigned_to = WorkflowService._resolve_actor(
            next_step.step.assigned_role,
            workflow_run,
        )

        next_step.status = WorkflowStepRun.Status.IN_PROGRESS
        next_step.save(update_fields=["status", "assigned_to"])

    @staticmethod
    def _complete_workflow(workflow_run: WorkflowRun) -> None:
        workflow_run.status = WorkflowRun.Status.COMPLETED
        workflow_run.completed_at = timezone.now()
        workflow_run.save(update_fields=["status", "completed_at"])

    @staticmethod
    @transaction.atomic
    def record_decision(
        step_run_id: int,
        outcome: str,
        decided_by: str,
        comment: str = "",
    ) -> WorkflowDecision:
        step_run = WorkflowStepRun.objects.select_related("workflow_run", "step").get(id=step_run_id)

        if step_run.status != WorkflowStepRun.Status.IN_PROGRESS:
            raise ValueError("Only in-progress steps can be decided.")

        if step_run.decisions.exists():
            raise ValueError("This step has already been decided.")

        if step_run.workflow_run.status == WorkflowRun.Status.COMPLETED:
            raise ValueError("Completed workflows cannot be modified.")
        
        valid_outcomes = {choice[0] for choice in WorkflowDecision.Outcome.choices}

        if outcome not in valid_outcomes:
            raise ValueError(f"Invalid decision outcome: {outcome}")

        decision = WorkflowDecision.objects.create(
            step_run=step_run,
            outcome=outcome,
            decided_by=decided_by,
            comment=comment,
        )

        step_run.status = WorkflowStepRun.Status.COMPLETED
        step_run.completed_at = timezone.now()
        step_run.save(update_fields=["status", "completed_at"])

        if outcome == WorkflowDecision.Outcome.REJECTED:
            WorkflowService._complete_workflow(step_run.workflow_run)
        else:
            WorkflowService._activate_next_step(step_run.workflow_run)

        return decision
    
    @staticmethod
    def _resolve_actor(role, workflow_run):
        role_map = {
            "manager": workflow_run.started_by,
            "finance": "finance.user",
        }

        return role_map.get(role, "system")