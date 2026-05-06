from django.http import HttpResponseForbidden

from django.shortcuts import redirect
from django.views.generic import ListView, DetailView

from workflows.models import WorkflowRun, WorkflowStepRun
from workflows.forms import DecisionForm
from workflows.services import WorkflowService, WorkflowRunPageService


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

        page_service = WorkflowRunPageService(
            reference=self.object.reference,
            user=self.request.user,
        )

        context.update(page_service.build_context())
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        form = DecisionForm(request.POST)

        if not form.is_valid():
            return redirect("workflow-run-detail", reference=self.object.reference)

        active_step = self.object.step_runs.filter(
            status=WorkflowStepRun.Status.IN_PROGRESS
        ).first()

        if not active_step:
            return HttpResponseForbidden("No active step available.")

        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        if request.user.username != active_step.assigned_to:
            return HttpResponseForbidden("You are not allowed to decide this step.")

        WorkflowService.record_decision(
            step_run_id=active_step.id,
            outcome=form.cleaned_data["outcome"],
            decided_by=request.user.username,
            comment=form.cleaned_data["comment"],
        )

        return redirect("workflow-run-detail", reference=self.object.reference)