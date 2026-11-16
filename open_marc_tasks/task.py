import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, NamedTuple, Union

from pymarc import Record

from .commands.add_field import add_field
from .commands.delete_field import delete_field


class TaskError(ValueError):
    """Raised when a task file cannot be read or validated."""


class Task(NamedTuple):
    format_version: str
    name: str
    description: str
    steps: List[Dict[str, Any]]


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


def _validate_delete_field(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "tag"}, number)
    tag = _required(step, "tag", number)
    if not isinstance(tag, str) or len(tag) != 3 or any(
        char not in "0123456789X" for char in tag
    ):
        raise TaskError("step {} setting tag must be three digits or uppercase X".format(number))


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


def _validate_add_field(step: Dict[str, Any], number: int) -> None:
    allowed = {"command", "tag", "data", "ind1", "ind2", "subfields", "if_tag_exists", "when"}
    _unknown_settings(step, allowed, number)

    tag = _required(step, "tag", number)
    if not isinstance(tag, str) or len(tag) != 3 or any(char not in "0123456789" for char in tag):
        raise TaskError("step {} setting tag must be three digits".format(number))

    policy = step.get("if_tag_exists", "add")
    if policy not in ("add", "skip", "skip_if_identical"):
        raise TaskError("step {} setting if_tag_exists is invalid".format(number))
    if "when" in step:
        _validate_conditions(step["when"], number)

    if tag.startswith("00"):
        if any(setting in step for setting in ("ind1", "ind2", "subfields")):
            raise TaskError("step {} control field cannot have indicators or subfields".format(number))
        data = _required(step, "data", number)
        if not isinstance(data, str):
            raise TaskError("step {} setting data must be a string".format(number))
        return

    if "data" in step:
        raise TaskError("step {} data is only valid for control fields".format(number))
    for setting in ("ind1", "ind2"):
        value = _required(step, setting, number)
        if not isinstance(value, str) or len(value) != 1:
            raise TaskError("step {} setting {} must be one character".format(number, setting))

    subfields = _required(step, "subfields", number)
    if not isinstance(subfields, list) or not subfields:
        raise TaskError("step {} setting subfields must be a non-empty array".format(number))
    for pair in subfields:
        if not isinstance(pair, list) or len(pair) != 2:
            raise TaskError("step {} setting subfields must contain [code, value] pairs".format(number))
        code, value = pair
        if not isinstance(code, str) or len(code) != 1 or code not in "abcdefghijklmnopqrstuvwxyz0123456789":
            raise TaskError("step {} subfield code must be one lowercase letter or digit".format(number))
        if not isinstance(value, str):
            raise TaskError("step {} subfield value must be a string".format(number))


def _run_delete_field(record: Record, step: Dict[str, Any]) -> None:
    delete_field(record, step["tag"])


def _run_add_field(record: Record, step: Dict[str, Any]) -> None:
    add_field(record, step)


COMMANDS = {
    "delete_field": (_validate_delete_field, _run_delete_field),
    "add_field": (_validate_add_field, _run_add_field),
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
        for step in task.steps:
            _, runner = COMMANDS[step["command"]]
            runner(record, step)
        yield record
