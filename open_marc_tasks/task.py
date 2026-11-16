import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, NamedTuple, Union

from pymarc import Record

from .commands.delete_field import delete_field


class TaskError(ValueError):
    """Raised when a task file cannot be read or validated."""


class Task(NamedTuple):
    format_version: str
    name: str
    description: str
    steps: List[Dict[str, str]]


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
        if step["command"] != "delete_field":
            raise TaskError("step {} has unknown command: {!r}".format(number, step["command"]))
        unknown_settings = set(step) - {"command", "tag"}
        if unknown_settings:
            raise TaskError(
                "step {} has unknown setting: {}".format(number, sorted(unknown_settings)[0])
            )
        if "tag" not in step:
            raise TaskError("step {} is missing setting: tag".format(number))
        tag = step["tag"]
        if not isinstance(tag, str) or len(tag) != 3 or any(char not in "0123456789X" for char in tag):
            raise TaskError("step {} setting tag must be three digits or uppercase X".format(number))

    return Task(
        document["format_version"],
        document["name"],
        document["description"],
        document["steps"],
    )


def run_task(task: Task, records: Iterable[Record]) -> Iterator[Record]:
    for record in records:
        for step in task.steps:
            if step["command"] == "delete_field":
                delete_field(record, step["tag"])
        yield record
