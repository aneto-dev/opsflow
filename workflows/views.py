from django.shortcuts import redirect
from django.views.generic import ListView, DetailView
from workflows.models import WorkflowRun
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
        context["decision_form"] = WorkflowDecisionForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = WorkflowDecisionForm(request.POST)

        if form.is_valid():
            active_step = self.object.step_runs.filter(status="in_progress").first()

            if active_step:
                WorkflowService.record_decision(
                    step_run_id=active_step.id,
                    outcome=form.cleaned_data["outcome"],
                    decided_by=request.user.username if request.user.is_authenticated else "anonymous",
                    comment=form.cleaned_data["comment"],
                )

        return redirect("workflow-run-detail", reference=self.object.reference)