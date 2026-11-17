from typing import Any, Dict

from ..conditions import conditions_match
from ..regex_dialect import (
    RegexDialectError,
    compile_pattern,
    expand_replacement,
    validate_replacement,
)
from ..task import TaskError, _required, _unknown_settings, _validate_conditions
from ..text_form import parse_field, render_field


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "find", "replace", "regex", "when"}, number)
    find = _required(step, "find", number)
    if not isinstance(find, str) or not find:
        raise TaskError("step {} setting find must be a non-empty string".format(number))
    replacement = _required(step, "replace", number)
    if not isinstance(replacement, str):
        raise TaskError("step {} setting replace must be a string".format(number))
    regex = step.get("regex", False)
    if not isinstance(regex, bool):
        raise TaskError("step {} setting regex must be a boolean".format(number))
    if regex:
        try:
            compile_pattern(find)
            validate_replacement(replacement)
        except RegexDialectError as error:
            raise TaskError("step {} {}".format(number, error)) from error
    if "when" in step:
        _validate_conditions(step["when"], number)


def run(record, step):
    if not conditions_match(record, step.get("when", [])):
        return

    regex = step.get("regex", False)
    pattern = compile_pattern(step["find"]) if regex else None
    replacement = step["replace"]
    for index, field in enumerate(record.fields):
        text = render_field(field)
        if pattern is None:
            replaced = text.replace(step["find"], replacement)
        else:
            replaced = pattern.sub(
                lambda match: expand_replacement(match, replacement), text
            )
        if replaced != text:
            record.fields[index] = parse_field(replaced)
