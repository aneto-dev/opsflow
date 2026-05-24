from django.urls import path
from workflows.views import WorkflowRunListView, WorkflowRunDetailView
from workflows.views import WorkflowDecisionView

urlpatterns = [
    path("", WorkflowRunListView.as_view(), name="workflow-run-list"),
    path("<str:reference>/", WorkflowRunDetailView.as_view(), name="workflow-run-detail"),
    path("steps/<uuid:step_run_id>/decision/", WorkflowDecisionView.as_view(), name="workflow-decision",
),
]