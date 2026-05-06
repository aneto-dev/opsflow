from django import forms
from workflows.models import WorkflowDefinition, WorkflowDecision


class StartWorkflowForm(forms.Form):
    workflow = forms.ModelChoiceField(
        queryset=WorkflowDefinition.objects.filter(is_active=True).order_by("name"),
        empty_label="Select workflow",
    )
    reference = forms.CharField(max_length=100)
    started_by = forms.CharField(max_length=100)

class DecisionForm(forms.Form):
    outcome = forms.ChoiceField(
        choices=WorkflowDecision.Outcome.choices,
        widget=forms.RadioSelect,
    )

    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
