from typing import Any, Dict

from pymarc import Record, Subfield

from ..regex_dialect import RegexDialectError, compile_pattern
from ..task import TaskError, _required, _unknown_settings
from ..text_form import TextFormError


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(
        step,
        {
            "command",
            "tag",
            "code",
            "duplicates",
            "if_contains",
            "remove_text",
            "remove_regex",
        },
        number,
    )

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

    if "duplicates" in step and not isinstance(step["duplicates"], bool):
        raise TaskError("step {} setting duplicates must be a boolean".format(number))
    if "if_contains" in step:
        value = step["if_contains"]
        if not isinstance(value, str) or not value:
            raise TaskError("step {} setting if_contains must be a non-empty string".format(number))
    if "remove_text" in step:
        value = step["remove_text"]
        if not isinstance(value, str) or not value:
            raise TaskError("step {} setting remove_text must be a non-empty string".format(number))
    if "remove_regex" in step:
        value = step["remove_regex"]
        if not isinstance(value, str) or not value:
            raise TaskError("step {} setting remove_regex must be a non-empty string".format(number))
        try:
            compile_pattern(value)
        except RegexDialectError as error:
            raise TaskError("step {} {}".format(number, error)) from error
    if "duplicates" in step and any(
        setting in step for setting in ("if_contains", "remove_text", "remove_regex")
    ):
        raise TaskError(
            "step {} duplicates cannot be combined with if_contains, remove_text, "
            "or remove_regex".format(number)
        )
    if "if_contains" in step and "remove_text" in step:
        raise TaskError("step {} if_contains and remove_text cannot both be set".format(number))
    if "remove_regex" in step and ("if_contains" in step or "remove_text" in step):
        raise TaskError("step {} remove_regex cannot be combined with if_contains or remove_text".format(number))


def run(record: Record, step: Dict[str, Any]) -> None:
    code = step["code"]
    if step.get("duplicates", False):
        for field in record.get_fields(step["tag"]):
            seen_values = set()
            unique_subfields = []
            for subfield in field.subfields:
                if subfield.code == code:
                    if subfield.value in seen_values:
                        continue
                    seen_values.add(subfield.value)
                unique_subfields.append(subfield)
            field.subfields = unique_subfields
        return

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

    if "remove_regex" in step:
        pattern = compile_pattern(step["remove_regex"])
        for field in record.get_fields(step["tag"]):
            edited_subfields = []
            for subfield in field.subfields:
                if subfield.code != code:
                    edited_subfields.append(subfield)
                    continue
                result = pattern.sub("", subfield.code + subfield.value)
                if not result:
                    continue
                if not (result[0].isascii() and result[0].isalnum()):
                    raise TextFormError("regex result has an invalid subfield code")
                edited_subfields.append(Subfield(result[0], result[1:]))
            field.subfields = edited_subfields
            if not field.subfields:
                record.remove_field(field)
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
