from typing import Any, Dict

from pymarc import Field, Record, Subfield

from ..conditions import conditions_match


def _identical(left: Field, right: Field) -> bool:
    if left.is_control_field():
        return left.data == right.data
    return left.indicators == right.indicators and [
        (subfield.code, subfield.value) for subfield in left.subfields
    ] == [(subfield.code, subfield.value) for subfield in right.subfields]


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

    if policy == "skip_if_identical" and existing:
        position = max(
            index for index, current in enumerate(record.fields) if current.tag == tag
        ) + 1
    else:
        position = next(
            (index for index, current in enumerate(record.fields) if current.tag >= tag),
            len(record.fields),
        )
    record.fields.insert(position, field)
