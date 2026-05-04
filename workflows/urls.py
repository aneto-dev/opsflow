from django.urls import path
from workflows.views import WorkflowRunListView, WorkflowRunDetailView

urlpatterns = [
    path("", WorkflowRunListView.as_view(), name="workflow-run-list"),
    path("<str:reference>/", WorkflowRunDetailView.as_view(), name="workflow-run-detail"),
]