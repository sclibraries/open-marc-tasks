from typing import Any, Dict, Optional

from pymarc import Record

from ..regex_dialect import RegexDialectError, compile_pattern
from ..task import TaskError, _required, _unknown_settings
from ..text_form import render_field


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(
        step,
        {"command", "tag", "match", "match_regex", "delete_nonmatches"},
        number,
    )
    tag = _required(step, "tag", number)
    if not isinstance(tag, str) or len(tag) != 3 or any(
        char not in "0123456789X" for char in tag
    ):
        raise TaskError("step {} setting tag must be three digits or uppercase X".format(number))
    match = step.get("match")
    if "match" in step and not isinstance(match, str):
        raise TaskError("step {} setting match must be a string".format(number))
    match_regex = step.get("match_regex", False)
    if not isinstance(match_regex, bool):
        raise TaskError("step {} setting match_regex must be a boolean".format(number))
    delete_nonmatches = step.get("delete_nonmatches", False)
    if not isinstance(delete_nonmatches, bool):
        raise TaskError("step {} setting delete_nonmatches must be a boolean".format(number))
    if match_regex and "match" not in step:
        raise TaskError("step {} setting match_regex requires match".format(number))
    if delete_nonmatches and "match" not in step:
        raise TaskError("step {} setting delete_nonmatches requires match".format(number))
    if match_regex:
        try:
            compile_pattern(match)
        except RegexDialectError as error:
            raise TaskError("step {} {}".format(number, error)) from error


def _matches(field_tag: str, tag_pattern: str) -> bool:
    if "X" not in tag_pattern:
        return field_tag == tag_pattern
    prefix = tag_pattern.rstrip("X")
    if "X" in prefix:
        return False
    return field_tag.startswith(prefix)


def _matches_text(field, match: str) -> bool:
    return match in render_field(field)


def delete_field(
    record: Record,
    tag: str,
    match: Optional[str] = None,
    match_regex: bool = False,
    delete_nonmatches: bool = False,
) -> None:
    """Delete fields matching the tag and, when set, the field-text filter."""
    pattern = compile_pattern(match) if match_regex else None

    def keep(field):
        if not _matches(field.tag, tag):
            return True
        if match is None:
            return False
        matches_text = (
            pattern.search(render_field(field)) is not None
            if pattern is not None
            else _matches_text(field, match)
        )
        return matches_text if delete_nonmatches else not matches_text

    record.fields[:] = [field for field in record.fields if keep(field)]


def run(record: Record, step: Dict[str, Any]) -> None:
    delete_field(
        record,
        step["tag"],
        step.get("match"),
        step.get("match_regex", False),
        step.get("delete_nonmatches", False),
    )
