import re
from typing import Any, Dict

from pymarc import Record, Subfield

from ..conditions import conditions_match
from ..regex_dialect import (
    RegexDialectError,
    compile_pattern,
    expand_replacement,
    validate_replacement,
)
from ..task import TaskError, _required, _unknown_settings, _validate_conditions
from ..text_form import TextFormError


_ACTIONS = (
    "add",
    "add_if_missing",
    "replace",
    "replace_first",
    "replace_regex",
    "append",
    "prepend",
    "clear",
)
_VALUE_ACTIONS = ("add", "add_if_missing", "append", "prepend")
_REPLACE_ACTIONS = ("replace", "replace_first")


def validate(step: Dict[str, Any], number: int) -> None:
    allowed = {"command", "tag", "code", "action", "value", "find", "replace", "when"}
    _unknown_settings(step, allowed, number)

    tag = _required(step, "tag", number)
    if not isinstance(tag, str) or len(tag) != 3 or any(char not in "0123456789" for char in tag):
        raise TaskError("step {} setting tag must be three digits".format(number))

    code = _required(step, "code", number)
    if not isinstance(code, str) or len(code) != 1 or code not in "abcdefghijklmnopqrstuvwxyz0123456789":
        raise TaskError("step {} setting code must be one lowercase letter or digit".format(number))

    action = _required(step, "action", number)
    if not isinstance(action, str) or action not in _ACTIONS:
        raise TaskError("step {} setting action is invalid".format(number))
    if "when" in step:
        _validate_conditions(step["when"], number)

    if action in _VALUE_ACTIONS:
        if "find" in step or "replace" in step:
            raise TaskError("step {} find and replace are not valid for action {}".format(number, action))
        value = _required(step, "value", number)
        if not isinstance(value, str):
            raise TaskError("step {} setting value must be a string".format(number))
    elif action in _REPLACE_ACTIONS or action == "replace_regex":
        if "value" in step:
            raise TaskError("step {} value is not valid for action {}".format(number, action))
        find = _required(step, "find", number)
        if not isinstance(find, str) or not find:
            raise TaskError("step {} setting find must be a non-empty string".format(number))
        replacement = _required(step, "replace", number)
        if not isinstance(replacement, str):
            raise TaskError("step {} setting replace must be a string".format(number))
        if action == "replace_regex":
            try:
                compile_pattern(find)
                validate_replacement(replacement)
            except RegexDialectError as error:
                raise TaskError("step {} {}".format(number, error)) from error
    elif any(setting in step for setting in ("value", "find", "replace")):
        raise TaskError("step {} clear does not accept value, find, or replace".format(number))


def run(record: Record, step: Dict[str, Any]) -> None:
    if not conditions_match(record, step.get("when", [])):
        return

    code = step["code"]
    action = step["action"]
    pattern = compile_pattern(step["find"]) if action == "replace_regex" else None
    for field in record.get_fields(step["tag"]):
        if field.is_control_field():
            continue
        if action == "add":
            field.subfields.append(Subfield(code, step["value"]))
        elif action == "add_if_missing":
            if not any(subfield.code == code for subfield in field.subfields):
                field.subfields.append(Subfield(code, step["value"]))
        elif action == "replace_regex":
            edited_subfields = []
            for subfield in field.subfields:
                if subfield.code != code:
                    edited_subfields.append(subfield)
                    continue
                result = pattern.sub(
                    lambda match: expand_replacement(match, step["replace"]),
                    subfield.code + subfield.value,
                )
                if not result:
                    continue
                if not (result[0].isascii() and result[0].isalnum()):
                    raise TextFormError("regex result has an invalid subfield code")
                edited_subfields.append(Subfield(result[0], result[1:]))
            field.subfields = edited_subfields
        else:
            for index, subfield in enumerate(field.subfields):
                if subfield.code != code:
                    continue
                if action == "append":
                    value = subfield.value + step["value"]
                elif action == "prepend":
                    value = step["value"] + subfield.value
                elif action == "replace":
                    value = subfield.value.replace(step["find"], step["replace"])
                elif action == "replace_first":
                    match = re.search(re.escape(step["find"]), subfield.value, re.IGNORECASE)
                    if match:
                        value = (
                            subfield.value[: match.start()]
                            + step["replace"]
                            + subfield.value[match.end() :]
                        )
                    else:
                        value = subfield.value
                else:
                    value = ""
                field.subfields[index] = Subfield(code, value)
