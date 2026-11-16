import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, NamedTuple, Union

from pymarc import Record


class TaskError(ValueError):
    """Raised when a task file cannot be read or validated."""


class Task(NamedTuple):
    format_version: str
    name: str
    description: str
    steps: List[Dict[str, Any]]


def blank_backslash_indicators(record: Record) -> None:
    for field in record.get_fields():
        if field.indicators is not None and "\\" in field.indicators:
            field.indicators = tuple(
                " " if indicator == "\\" else indicator
                for indicator in field.indicators
            )


def _unknown_settings(step: Dict[str, Any], allowed: set, number: int) -> None:
    unknown = set(step) - allowed
    if unknown:
        raise TaskError(
            "step {} has unknown setting: {}".format(number, sorted(unknown)[0])
        )


def _required(step: Dict[str, Any], setting: str, number: int) -> Any:
    if setting not in step:
        raise TaskError("step {} is missing setting: {}".format(number, setting))
    return step[setting]


def _validate_conditions(conditions: Any, number: int) -> None:
    if not isinstance(conditions, list):
        raise TaskError("step {} setting when must be an array".format(number))
    for condition in conditions:
        if not isinstance(condition, dict):
            raise TaskError("step {} setting when items must be objects".format(number))
        _unknown_settings(condition, {"leader", "in"}, number)
        leader = _required(condition, "leader", number)
        if isinstance(leader, bool) or not isinstance(leader, int) or not 0 <= leader <= 23:
            raise TaskError("step {} condition leader must be an integer from 0 through 23".format(number))
        values = _required(condition, "in", number)
        if not isinstance(values, list) or not values or any(
            not isinstance(value, str) or len(value) != 1 for value in values
        ):
            raise TaskError("step {} condition in must be a non-empty array of one-character strings".format(number))


from .commands.add_field import run as run_add_field
from .commands.add_field import validate as validate_add_field
from .commands.delete_field import run as run_delete_field
from .commands.delete_field import validate as validate_delete_field
from .commands.edit_subfield import run as run_edit_subfield
from .commands.edit_subfield import validate as validate_edit_subfield


COMMANDS = {
    "delete_field": (validate_delete_field, run_delete_field),
    "add_field": (validate_add_field, run_add_field),
    "edit_subfield": (validate_edit_subfield, run_edit_subfield),
}


def load_task(path: Union[str, Path]) -> Task:
    try:
        with open(path, "r", encoding="utf-8") as task_file:
            document = json.load(task_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TaskError("could not read task: {}".format(error)) from error

    if not isinstance(document, dict):
        raise TaskError("task must be a JSON object")

    required = {"format_version", "name", "description", "steps"}
    missing = required - set(document)
    unknown = set(document) - required
    if missing:
        raise TaskError("missing task property: {}".format(sorted(missing)[0]))
    if unknown:
        raise TaskError("unknown task property: {}".format(sorted(unknown)[0]))
    if document["format_version"] != "0.1":
        raise TaskError("unsupported format_version: {!r}".format(document["format_version"]))
    if not isinstance(document["name"], str):
        raise TaskError("task name must be a string")
    if not isinstance(document["description"], str):
        raise TaskError("task description must be a string")
    if not isinstance(document["steps"], list):
        raise TaskError("task steps must be an array")

    for number, step in enumerate(document["steps"], start=1):
        if not isinstance(step, dict):
            raise TaskError("step {} must be an object".format(number))
        if "command" not in step:
            raise TaskError("step {} is missing command".format(number))
        command = step["command"]
        if not isinstance(command, str) or command not in COMMANDS:
            raise TaskError("step {} has unknown command: {!r}".format(number, command))
        validator, _ = COMMANDS[command]
        validator(step, number)

    return Task(
        document["format_version"],
        document["name"],
        document["description"],
        document["steps"],
    )


def run_task(task: Task, records: Iterable[Record]) -> Iterator[Record]:
    for record in records:
        blank_backslash_indicators(record)
        for step in task.steps:
            _, runner = COMMANDS[step["command"]]
            runner(record, step)
        yield record
