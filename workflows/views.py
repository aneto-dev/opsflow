from django.shortcuts import redirect
from django.views.generic import ListView, DetailView
from workflows.models import WorkflowRun, WorkflowDecision
from workflows.forms import WorkflowDecisionForm
from workflows.services import WorkflowService


class WorkflowRunListView(ListView):
    model = WorkflowRun
    template_name = "workflows/run_list.html"
    context_object_name = "runs"
    paginate_by = 20
    ordering = ["-started_at"]


class WorkflowRunDetailView(DetailView):
    model = WorkflowRun
    template_name = "workflows/run_detail.html"
    context_object_name = "run"
    slug_field = "reference"
    slug_url_kwarg = "reference"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        active_step = self.object.step_runs.filter(status="in_progress").first()
        can_decide = (
            active_step
            and self.request.user.is_authenticated
            and self.request.user.username == active_step.assigned_to
        )

        context["decisions"] = (
            WorkflowDecision.objects
            .filter(step_run__workflow_run=self.object)
            .select_related("step_run", "step_run__step")
            .order_by("-decided_at")
        )
        context["active_step"] = active_step
        context["can_decide"] = can_decide
        context["decision_form"] = WorkflowDecisionForm()

        latest_decision = context["decisions"].first()

        if active_step:
            workflow_state_message = f"Waiting for {active_step.assigned_to} to review and decide"
        elif latest_decision and latest_decision.outcome == "rejected":
            workflow_state_message = "Workflow closed as rejected"
        elif latest_decision and latest_decision.outcome == "escalated":
            workflow_state_message = "Workflow escalated for external handling"
        else:
            workflow_state_message = "Workflow completed successfully"

        context["workflow_state_message"] = workflow_state_message

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.status == WorkflowRun.Status.COMPLETED:
            return redirect("workflow-run-detail", reference=self.object.reference)

        form = WorkflowDecisionForm(request.POST)

        if form.is_valid():
            active_step = self.object.step_runs.filter(status="in_progress").first()

            if not active_step:
                return redirect("workflow-run-detail", reference=self.object.reference)

            if not request.user.is_authenticated:
                return redirect("workflow-run-detail", reference=self.object.reference)

            if request.user.username != active_step.assigned_to:
                return redirect("workflow-run-detail", reference=self.object.reference)
            
            if active_step.decisions.exists():
                return redirect("workflow-run-detail", reference=self.object.reference)

            if active_step:
                WorkflowService.record_decision(
                    step_run_id=active_step.id,
                    outcome=form.cleaned_data["outcome"],
                    decided_by=request.user.username if request.user.is_authenticated else "anonymous",
                    comment=form.cleaned_data["comment"],
                )

        return redirect("workflow-run-detail", reference=self.object.reference)