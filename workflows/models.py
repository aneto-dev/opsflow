from django.db import models


class WorkflowDefinition(models.Model):
    name = models.CharField(max_length=150)
    key = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_definitions"
        ordering = ["name"]

    def __str__(self):
        return self.name
    
class WorkflowRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.PROTECT,
        related_name="runs"
    )
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    started_by = models.CharField(max_length=255)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.reference
    
class WorkflowStep(models.Model):
    workflow = models.ForeignKey(
            WorkflowDefinition,
            on_delete=models.CASCADE,
            related_name="steps"
    )
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField()
    is_required = models.BooleanField(default=True)
    assigned_role = models.CharField(max_length=100)

    class Meta:
            ordering = ["workflow", "order"]
            unique_together = ("workflow", "order")

    def __str__(self):
        return f"{self.workflow.key} :: Step {self.order} - {self.name}"
    

class WorkflowStepRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    workflow_run = models.ForeignKey(
        WorkflowRun,
        on_delete=models.CASCADE,
        related_name="step_runs"
    )
    step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.PROTECT,
        related_name="runs"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    assigned_to = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["workflow_run", "step__order"]
        unique_together = ("workflow_run", "step")

    def __str__(self):
        return f"{self.workflow_run.reference} :: {self.step.name}"
    
    
class WorkflowDecision(models.Model):
        class Outcome(models.TextChoices):
            APPROVED = "approved", "Approved"
            REJECTED = "rejected", "Rejected"
            SENT_BACK = "sent_back", "Sent Back"
            ESCALATED = "escalated", "Escalated"

        step_run = models.ForeignKey(
            WorkflowStepRun,
            on_delete=models.CASCADE,
            related_name="decisions"
        )
        outcome = models.CharField(
            max_length=20,
            choices=Outcome.choices
        )
        decided_by = models.CharField(max_length=255)
        comment = models.TextField(blank=True)
        decided_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
            return f"{self.step_run} :: {self.outcome}"