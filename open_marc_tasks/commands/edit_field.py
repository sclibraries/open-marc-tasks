from typing import Any, Dict

from ..task import TaskError, _required, _unknown_settings
from ..text_form import parse_field, render_field
from .replace_text import _build_replacer, validate as validate_replace_text


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "tag", "find", "replace", "regex"}, number)
    tag = _required(step, "tag", number)
    if not isinstance(tag, str) or len(tag) != 3 or not tag.isascii() or not tag.isdigit():
        raise TaskError("step {} setting tag must be three ASCII digits".format(number))
    validate_replace_text(
        {key: value for key, value in step.items() if key != "tag"}, number
    )


def run(record, step):
    replace = _build_replacer(step)
    for index, field in enumerate(record.fields):
        if field.tag != step["tag"]:
            continue

        text = render_field(field)
        is_control = field.is_control_field()
        body_start = 6 if is_control else 8
        original_body = text[body_start:]
        body = replace(original_body)
        if body == original_body:
            continue

        if not is_control:
            first_subfield = body.find("$")
            body = body[first_subfield:] if first_subfield >= 0 else ""
        record.fields[index] = parse_field(text[:body_start] + body)
