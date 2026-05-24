from django.shortcuts import redirect
from django.views.generic import ListView, DetailView

from workflows.models import WorkflowRun, WorkflowStepRun
from workflows.services import WorkflowService, WorkflowRunPageService

from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib import messages

from workflows.forms import WorkflowDecisionForm
from workflows.permissions import WorkflowPermissionService

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

        context["decision_form"] = WorkflowDecisionForm()

        page_service = WorkflowRunPageService(
            reference=self.object.reference,
            user=self.request.user,
        )

        context.update(page_service.build_context())
        return context

class WorkflowDecisionView(View):

    def post(self, request, step_run_id):

        step_run = get_object_or_404(
            WorkflowStepRun,
            id=step_run_id,
        )

        if not WorkflowPermissionService.can_decide_step(
            user=request.user,
            step_run=step_run,
        ):
            messages.error(
                request,
                "You do not have permission to decide this workflow step.",
            )

            return redirect(
                "workflow-run-detail",
                reference=step_run.workflow_run.reference,
            )

        form = WorkflowDecisionForm(request.POST)

        if not form.is_valid():
            messages.error(
                request,
                "Invalid workflow decision.",
            )

            return redirect(
                "workflow-run-detail",
                reference=step_run.workflow_run.reference,
            )

        WorkflowService.record_decision(
            step_run_id=step_run.id,
            outcome=form.cleaned_data["decision"],
            decided_by=request.user.username,
            comment=form.cleaned_data["comment"],
        )

        messages.success(
            request,
            "Workflow decision recorded.",
        )

        return redirect(
            "workflow-run-detail",
            reference=step_run.workflow_run.reference,
        )