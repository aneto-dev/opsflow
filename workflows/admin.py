from django.contrib import admin
from workflows.models import WorkflowDefinition,WorkflowRun
from django.utils.html import format_html
from workflows.services import WorkflowService

from workflows.models import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowRun,
    WorkflowStepRun,
    WorkflowDecision,
)

@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "is_active", "created_at", "updated_at")
    search_fields = ("name", "key")
    list_filter = ("is_active",)
    ordering = ("name",)

class WorkflowStepRunInline(admin.TabularInline):
    model = WorkflowStepRun
    extra = 0
    fields = ("step", "assigned_to", "status_badge", "started_at", "completed_at")
    readonly_fields = ("step", "assigned_to", "status_badge", "started_at", "completed_at")
    can_delete = False
    show_change_link = True

    def status_badge(self, obj):
        colors = {
            "pending": "#f59e0b",
            "in_progress": "#3b82f6",
            "completed": "#10b981",
        }

        color = colors.get(obj.status, "#6b7280")

        label = obj.status.replace("_", " ").title()

        return format_html(
            '<strong style="color: {};">● {}</strong>',
            color,
            label,
        )

@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = ("reference", "workflow", "status", "started_by", "started_at", "completed_at")
    search_fields = ("reference", "started_by")
    list_filter = ("status", "workflow")
    ordering = ("-started_at",)
    inlines = [WorkflowStepRunInline]


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ("workflow", "order", "name", "assigned_role", "is_required")
    search_fields = ("name", "assigned_role", "workflow__name", "workflow__key")
    list_filter = ("workflow", "is_required", "assigned_role")
    ordering = ("workflow", "order")


@admin.register(WorkflowStepRun)
class WorkflowStepRunAdmin(admin.ModelAdmin):
    actions = ["approve_steps", "reject_steps"]

    list_display = (
        "workflow_run",
        "step",
        "assigned_to",
        "status_badge",
        "started_at",
        "completed_at",
    )
    search_fields = ("workflow_run__reference", "step__name", "assigned_to")
    list_filter = ("status", "assigned_to")
    ordering = ("workflow_run", "step__order")

    def status_badge(self, obj):
        colors = {
            "pending": "#f59e0b",
            "in_progress": "#3b82f6",
            "completed": "#10b981",
        }

        color = colors.get(obj.status, "#6b7280")
        label = obj.status.replace("_", " ").title()

        return format_html(
            '<strong style="color: {};">● {}</strong>',
            color,
            label,
        )
    
    @admin.action(description="Approve selected steps")
    def approve_steps(self, request, queryset):
        for step_run in queryset:
            WorkflowService.record_decision(
                step_run_id=step_run.id,
                outcome="approved",
                decided_by=request.user.username,
                comment="Approved via admin",
            )
    @admin.action(description="Reject selected steps")
    def reject_steps(self, request, queryset):
        for step_run in queryset:
            WorkflowService.record_decision(
                step_run_id=step_run.id,
                outcome="rejected",
                decided_by=request.user.username,
                comment="Rejected via admin",
            )

@admin.register(WorkflowDecision)
class WorkflowDecisionAdmin(admin.ModelAdmin):
    list_display = ("step_run", "outcome", "decided_by", "decided_at")
    search_fields = ("step_run__workflow_run__reference", "decided_by", "comment")
    list_filter = ("outcome", "decided_at")
    ordering = ("-decided_at",)