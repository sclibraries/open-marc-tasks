from typing import Any, Dict

from ..task import TaskError, _required, _unknown_settings


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "tag", "value", "if_starts_with"}, number)

    tag = _required(step, "tag", number)
    if not isinstance(tag, str) or len(tag) != 3 or not tag.isascii() or not tag.isdigit():
        raise TaskError("step {} setting tag must be three ASCII digits".format(number))

    value = _required(step, "value", number)
    if not isinstance(value, str) or len(value) not in (1, 2):
        raise TaskError("step {} setting value must be one or two characters".format(number))

    if "if_starts_with" in step:
        prefix = step["if_starts_with"]
        if not isinstance(prefix, str) or len(prefix) not in (1, 2):
            raise TaskError("step {} setting if_starts_with must be one or two characters".format(number))


def run(record, step: Dict[str, Any]) -> None:
    prefix = step.get("if_starts_with")
    value = step["value"]
    for field in record.get_fields(step["tag"]):
        if field.indicators is None:
            continue
        indicators = "".join(field.indicators)
        if prefix is not None and not indicators.startswith(prefix):
            continue
        field.indicators = tuple(value + indicators[len(value):])
