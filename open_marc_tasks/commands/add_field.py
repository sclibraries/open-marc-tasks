from typing import Any, Dict, List, Optional

from pymarc import Field, Record, Subfield

from ..conditions import conditions_match
from ..task import TaskError, _required, _unknown_settings, _validate_conditions


def validate(step: Dict[str, Any], number: int) -> None:
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


def _identical(left: Field, right: Field) -> bool:
    if left.is_control_field():
        return left.data == right.data
    return left.indicators == right.indicators and [
        (subfield.code, subfield.value) for subfield in left.subfields
    ] == [(subfield.code, subfield.value) for subfield in right.subfields]


def insert_fields(
    record: Record, fields: List[Field], position: Optional[int] = None
) -> None:
    if position is None:
        tag = fields[0].tag
        position = next(
            (index for index, current in enumerate(record.fields) if current.tag >= tag),
            len(record.fields),
        )
    record.fields[position:position] = fields


def add_field(record: Record, settings: Dict[str, Any]) -> None:
    """Add a validated data or control field in MarcEdit tag order."""
    if not conditions_match(record, settings.get("when", [])):
        return

    tag = settings["tag"]
    policy = settings.get("if_tag_exists", "add")
    existing = record.get_fields(tag)
    if policy == "skip" and existing:
        return

    if tag.startswith("00"):
        field = Field(tag=tag, data=settings["data"])
    else:
        field = Field(
            tag=tag,
            indicators=[settings["ind1"], settings["ind2"]],
            subfields=[Subfield(code, value) for code, value in settings["subfields"]],
        )

    if policy == "skip_if_identical" and any(
        _identical(field, candidate) for candidate in existing
    ):
        return

    position = None
    if policy == "skip_if_identical" and existing:
        position = max(
            index for index, current in enumerate(record.fields) if current.tag == tag
        ) + 1
    insert_fields(record, [field], position)


def run(record: Record, step: Dict[str, Any]) -> None:
    add_field(record, step)
