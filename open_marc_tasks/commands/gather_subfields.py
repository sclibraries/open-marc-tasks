from typing import Any, Dict

from pymarc import Record, Subfield

from ..task import TaskError, _required, _unknown_settings


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(
        step,
        {"command", "from_tag", "code", "to_tag", "remove_source"},
        number,
    )

    for setting in ("from_tag", "to_tag"):
        tag = _required(step, setting, number)
        if not isinstance(tag, str) or len(tag) != 3 or any(
            char not in "0123456789" for char in tag
        ):
            raise TaskError("step {} setting {} must be three digits".format(number, setting))
        if tag.startswith("00"):
            raise TaskError(
                "step {} setting {} must be a data-field tag".format(number, setting)
            )

    code = _required(step, "code", number)
    if (
        not isinstance(code, str)
        or len(code) != 1
        or code not in "abcdefghijklmnopqrstuvwxyz0123456789"
    ):
        raise TaskError(
            "step {} setting code must be one lowercase letter or digit".format(number)
        )

    remove_source = step.get("remove_source", False)
    if not isinstance(remove_source, bool):
        raise TaskError("step {} setting remove_source must be a boolean".format(number))


def run(record: Record, step: Dict[str, Any]) -> None:
    code = step["code"]
    for source in record.get_fields(step["from_tag"]):
        first = next(
            (
                index
                for index, subfield in enumerate(source.subfields)
                if subfield.code == code
            ),
            None,
        )
        if first is None:
            continue

        source_index = record.fields.index(source)
        target = next(
            (
                field
                for field in reversed(record.fields[source_index + 1 :])
                if field.tag == step["to_tag"]
            ),
            None,
        )
        if target is None:
            continue

        target.subfields.extend(
            Subfield(subfield.code, subfield.value)
            for subfield in source.subfields[first:]
        )
        if step.get("remove_source", False):
            record.remove_field(source)
