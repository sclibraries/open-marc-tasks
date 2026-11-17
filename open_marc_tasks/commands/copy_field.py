from typing import Any, Dict

from pymarc import Field, Record, Subfield

from ..task import TaskError, _required, _unknown_settings
from ..text_form import parse_field, render_field
from .add_field import insert_fields
from .delete_field import _matches_text


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "from_tag", "to_tag", "move", "if_contains"}, number)

    tags = {}
    for setting in ("from_tag", "to_tag"):
        tag = _required(step, setting, number)
        if not isinstance(tag, str) or len(tag) != 3 or any(
            char not in "0123456789" for char in tag
        ):
            raise TaskError("step {} setting {} must be three digits".format(number, setting))
        tags[setting] = tag

    if tags["from_tag"] == tags["to_tag"]:
        raise TaskError("step {} setting from_tag must differ from to_tag".format(number))

    move = step.get("move", False)
    if not isinstance(move, bool):
        raise TaskError("step {} setting move must be a boolean".format(number))

    if "if_contains" in step and (
        not isinstance(step["if_contains"], str) or not step["if_contains"]
    ):
        raise TaskError("step {} setting if_contains must be a non-empty string".format(number))

    if not tags["from_tag"].startswith("00") and tags["to_tag"].startswith("00"):
        raise TaskError("step {} cannot copy a data field to a control tag".format(number))


def run(record: Record, step: Dict[str, Any]) -> None:
    from_tag = step["from_tag"]
    to_tag = step["to_tag"]
    source_fields = [
        field
        for field in record.get_fields(from_tag)
        if "if_contains" not in step or _matches_text(field, step["if_contains"])
    ]
    if not source_fields:
        return

    if from_tag.startswith("00") and not to_tag.startswith("00"):
        copied_fields = [
            parse_field("={}  \\\\$a{}".format(to_tag, render_field(field)[6:]))
            for field in source_fields
        ]
    elif from_tag.startswith("00"):
        copied_fields = [Field(tag=to_tag, data=field.data) for field in source_fields]
    else:
        copied_fields = [
            Field(
                tag=to_tag,
                indicators=field.indicators,
                subfields=[Subfield(subfield.code, subfield.value) for subfield in field.subfields],
            )
            for field in source_fields
        ]

    if step.get("move", False):
        source_ids = {id(field) for field in source_fields}
        record.fields[:] = [field for field in record.fields if id(field) not in source_ids]

    position = None
    if not from_tag.startswith("00"):
        matching_targets = [
            index for index, field in enumerate(record.fields) if field.tag == to_tag
        ]
        if matching_targets:
            position = matching_targets[-1] + 1
    insert_fields(record, copied_fields, position)
