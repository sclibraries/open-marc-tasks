from typing import Any, Dict

from ..task import TaskError, _required, _unknown_settings


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "task"}, number)
    task = _required(step, "task", number)
    if (
        not isinstance(task, str)
        or len(task) < 6
        or not task.endswith(".json")
        or "/" in task
        or "\\" in task
    ):
        raise TaskError(
            "step {} setting task must be a .json file name without path separators".format(
                number
            )
        )


def run(record, step: Dict[str, Any]) -> None:
    from ..task import _run_called_task

    _run_called_task(record, step.task, step["task"])
