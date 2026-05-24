from django.db import transaction
from django.utils import timezone
from workflows.forms import WorkflowDecisionForm

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
    def _activate_previous_step(workflow_run: WorkflowRun, current_step_run: WorkflowStepRun) -> None:
        previous_step = (
            WorkflowStepRun.objects
            .filter(
                workflow_run=workflow_run,
                step__order__lt=current_step_run.step.order,
            )
            .order_by("-step__order")
            .first()
        )

        if not previous_step:
            WorkflowService._complete_workflow(workflow_run)
            return

        previous_step.status = WorkflowStepRun.Status.IN_PROGRESS
        previous_step.assigned_to = WorkflowService._resolve_actor(
            previous_step.step.assigned_role,
            workflow_run,
        )
        previous_step.completed_at = None
        previous_step.save(update_fields=["status", "assigned_to", "completed_at"])

    @staticmethod
    def _complete_workflow(workflow_run: WorkflowRun) -> None:
            workflow_run.status = WorkflowRun.Status.COMPLETED
            workflow_run.completed_at = timezone.now()
            workflow_run.save(update_fields=["status", "completed_at"])

    @staticmethod
    @transaction.atomic
    def record_decision(
        step_run_id: str,
        outcome: str,
        decided_by: str,
        comment: str,
    ) -> WorkflowDecision:

        step_run = (
            WorkflowStepRun.objects
            .select_related("workflow_run", "step")
            .get(id=step_run_id)
        )

        if step_run.status != WorkflowStepRun.Status.IN_PROGRESS:
            raise ValueError("Only in-progress steps can be decided.")

        if step_run.decisions.exists():
            raise ValueError("This step has already been decided.")

        if step_run.workflow_run.status == WorkflowRun.Status.COMPLETED:
            raise ValueError("Completed workflows cannot be modified.")

        valid_outcomes = {
            choice[0]
            for choice in WorkflowDecision.Outcome.choices
        }

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

        step_run.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        if outcome == WorkflowDecision.Outcome.REJECTED:

            WorkflowService._complete_workflow(
                step_run.workflow_run
            )

        elif outcome == WorkflowDecision.Outcome.SENT_BACK:

            step_run.status = WorkflowStepRun.Status.PENDING
            step_run.completed_at = None

            step_run.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            WorkflowService._activate_previous_step(
                step_run.workflow_run,
                step_run,
            )

        else:

            WorkflowService._activate_next_step(
                step_run.workflow_run
            )

        return decision
    
    @staticmethod
    def _resolve_actor(role, workflow_run):
        role_map = {
            "manager": workflow_run.started_by,
            "finance": "finance.user",
        }

        return role_map.get(role, "system")
    


class WorkflowRunPageService:
    def __init__(self, reference, user):
        self.reference = reference
        self.user = user
        self.run = self._get_run()

    def _get_run(self):
        return (
            WorkflowRun.objects
            .select_related("workflow")
            .prefetch_related(
                "step_runs__step",
                "step_runs__decisions",
            )
            .get(reference=self.reference)
        )
    
    def _can_decide(self, active_step):
        return (
            active_step
            and self.user.is_authenticated
            and self.user.username == active_step.assigned_to
        )
    
    def _get_workflow_state_message(self, active_step):
        latest_decision = self._get_decisions().first()

        if active_step:
            return f"Waiting for {active_step.assigned_to} to review and decide"

        if latest_decision and latest_decision.outcome == WorkflowDecision.Outcome.REJECTED:
            return "Workflow closed as rejected"

        if (latest_decision
            and latest_decision.outcome == WorkflowDecision.Outcome.ESCALATED
            and active_step
        ):
            return "Workflow escalated for external handling"

        return "Workflow completed successfully"

    def build_context(self):
        active_step = self._get_active_step()

        return {
            "run": self.run,
            "active_step": active_step,
            "can_decide": self._can_decide(active_step),
            "decision_form": WorkflowDecisionForm(),
            "workflow_state_message": self._get_workflow_state_message(active_step),
            "decisions": self._get_decisions(),
        }

    def _get_active_step(self):
        return self.run.step_runs.filter(
            status=WorkflowStepRun.Status.IN_PROGRESS
        ).first()
    
    def _get_decisions(self):
        return (
            WorkflowDecision.objects
            .filter(step_run__workflow_run=self.run)
            .select_related("step_run", "step_run__step")
            .order_by("-decided_at")
        )