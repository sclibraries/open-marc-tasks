from typing import Any, Dict

from ..conditions import conditions_match
from ..task import TaskError, _required, _unknown_settings, _validate_conditions
from ..text_form import parse_field, render_field


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "find", "replace", "when"}, number)
    find = _required(step, "find", number)
    if not isinstance(find, str) or not find:
        raise TaskError("step {} setting find must be a non-empty string".format(number))
    replacement = _required(step, "replace", number)
    if not isinstance(replacement, str):
        raise TaskError("step {} setting replace must be a string".format(number))
    if "when" in step:
        _validate_conditions(step["when"], number)


def run(record, step):
    if not conditions_match(record, step.get("when", [])):
        return

    for index, field in enumerate(record.fields):
        text = render_field(field)
        replaced = text.replace(step["find"], step["replace"])
        if replaced != text:
            record.fields[index] = parse_field(replaced)
