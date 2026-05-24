class WorkflowPermissionService:

    @staticmethod
    def can_decide_step(user, step_run):

        if not user.is_authenticated:
            return False

        return (
            step_run.status == step_run.Status.IN_PROGRESS
            and user.username == step_run.assigned_to
        )