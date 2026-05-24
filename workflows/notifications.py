from workflows.models import WorkflowNotification


class WorkflowNotificationService:

    @staticmethod
    def create_notification(
        workflow_run,
        recipient,
        message,
    ):

        return WorkflowNotification.objects.create(
            workflow_run=workflow_run,
            recipient=recipient,
            message=message,
        )