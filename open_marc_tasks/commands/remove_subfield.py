from typing import Any, Dict

from pymarc import Record, Subfield

from ..task import TaskError, _required, _unknown_settings


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "tag", "code", "if_contains", "remove_text"}, number)

    tag = _required(step, "tag", number)
    if not isinstance(tag, str) or len(tag) != 3 or any(
        char not in "0123456789" for char in tag
    ):
        raise TaskError("step {} setting tag must be three digits".format(number))
    if tag.startswith("00"):
        raise TaskError("step {} setting tag must be a data-field tag".format(number))

    code = _required(step, "code", number)
    if not isinstance(code, str) or len(code) != 1 or code not in "abcdefghijklmnopqrstuvwxyz0123456789":
        raise TaskError("step {} setting code must be one lowercase letter or digit".format(number))

    if "if_contains" in step:
        value = step["if_contains"]
        if not isinstance(value, str) or not value:
            raise TaskError("step {} setting if_contains must be a non-empty string".format(number))
    if "remove_text" in step:
        value = step["remove_text"]
        if not isinstance(value, str) or not value:
            raise TaskError("step {} setting remove_text must be a non-empty string".format(number))
    if "if_contains" in step and "remove_text" in step:
        raise TaskError("step {} if_contains and remove_text cannot both be set".format(number))


def run(record: Record, step: Dict[str, Any]) -> None:
    code = step["code"]
    if "remove_text" in step:
        text = step["remove_text"]
        for field in record.get_fields(step["tag"]):
            field.subfields = [
                Subfield(subfield.code, subfield.value.replace(text, ""))
                if subfield.code == code
                else subfield
                for subfield in field.subfields
            ]
        return

    if_contains = step.get("if_contains")
    for field in record.get_fields(step["tag"]):
        field.subfields = [
            subfield
            for subfield in field.subfields
            if subfield.code != code
            or (if_contains is not None and if_contains not in subfield.value)
        ]
        if not field.subfields:
            record.remove_field(field)
