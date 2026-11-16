from typing import Any, Dict

from pymarc import Record

from ..task import TaskError, _required, _unknown_settings


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "tag"}, number)
    tag = _required(step, "tag", number)
    if not isinstance(tag, str) or len(tag) != 3 or any(
        char not in "0123456789X" for char in tag
    ):
        raise TaskError("step {} setting tag must be three digits or uppercase X".format(number))


def _matches(field_tag: str, tag_pattern: str) -> bool:
    if "X" not in tag_pattern:
        return field_tag == tag_pattern
    prefix = tag_pattern.rstrip("X")
    if "X" in prefix:
        return False
    return field_tag.startswith(prefix)


def delete_field(record: Record, tag: str) -> None:
    """Delete every field matching a validated tag pattern, in place."""
    record.fields[:] = [field for field in record.fields if not _matches(field.tag, tag)]


def run(record: Record, step: Dict[str, Any]) -> None:
    delete_field(record, step["tag"])
