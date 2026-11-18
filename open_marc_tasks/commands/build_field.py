import re
from typing import Any, Dict, Optional

from pymarc import Field, Record

from ..conditions import conditions_match
from ..task import TaskError, _required, _unknown_settings, _validate_conditions
from ..text_form import TextFormError, parse_field, render_field
from .add_field import insert_fields


_BRACE_EXPRESSION = re.compile(r"\{[^{}]*\}")
_PLACEHOLDER = re.compile(r"\{([0-9]{3})(?:\$([a-z0-9])(\[x\])?)?\}")
_TEXT_FORM_ESCAPES = {"{dollar}", "{lcub}", "{rcub}", "{bsol}"}


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "field", "mode", "when"}, number)

    field = _required(step, "field", number)
    if not isinstance(field, str):
        raise TaskError("step {} setting field must be a string".format(number))

    mode = step.get("mode", "add")
    if mode not in ("add", "add_if_missing", "replace"):
        raise TaskError("step {} setting mode is invalid".format(number))
    if "when" in step:
        _validate_conditions(step["when"], number)

    x_count = 0
    has_whole_data_field_placeholder = False
    for expression in _BRACE_EXPRESSION.finditer(field):
        token = expression.group(0)
        if token in _TEXT_FORM_ESCAPES:
            continue
        placeholder = _PLACEHOLDER.fullmatch(token)
        if placeholder is None:
            raise TaskError(
                "step {} setting field has unsupported placeholder {!r}; "
                "source placeholders require a tag of three digits".format(number, token)
            )
        if placeholder.group(2) is None and placeholder.group(1) >= "010":
            has_whole_data_field_placeholder = True
        if placeholder.group(3):
            x_count += 1

    if x_count > 1:
        raise TaskError("step {} setting field supports only one [x] placeholder".format(number))
    if x_count and mode in ("add_if_missing", "replace"):
        raise TaskError("step {} setting mode {} cannot use [x]".format(number, mode))

    try:
        template_field = parse_field(_PLACEHOLDER.sub("", field))
    except TextFormError as error:
        raise TaskError("step {} setting field is invalid: {}".format(number, error)) from error
    if has_whole_data_field_placeholder and template_field.is_control_field():
        raise TaskError(
            "step {} setting field cannot use a whole data-field placeholder for a control field".format(
                number
            )
        )


def _subfield_text(field: Field, code: str) -> Optional[str]:
    if field.is_control_field() or not any(item.code == code for item in field.subfields):
        return None

    rendered = render_field(field)
    start = rendered.find("${}".format(code), 8) + 2
    end = rendered.find("$", start)
    return rendered[start:] if end == -1 else rendered[start:end]


def _source_text(record: Record, tag: str, code: Optional[str]) -> str:
    for field in record.get_fields(tag):
        if code is None:
            return render_field(field)[6:]
        value = _subfield_text(field, code)
        if value is not None:
            return value
    return ""


def run(record: Record, step: Dict[str, Any]) -> None:
    if not conditions_match(record, step.get("when", [])):
        return

    template = step["field"]
    tag = template[1:4]
    mode = step.get("mode", "add")
    if mode == "add_if_missing" and record.get_fields(tag):
        return
    replace_targets = record.get_fields(tag) if mode == "replace" else []
    if mode == "replace" and not replace_targets:
        return

    x_placeholder = next(
        (
            match
            for match in _PLACEHOLDER.finditer(template)
            if match.group(3) == "[x]"
        ),
        None,
    )
    if x_placeholder is None:
        expansions = [None]
    else:
        source_tag, code = x_placeholder.group(1), x_placeholder.group(2)
        expansions = [
            field
            for field in record.get_fields(source_tag)
            if _subfield_text(field, code) is not None
        ] or [None]

    built_fields = []
    for expansion in expansions:
        def substitute(match):
            source_tag, code, each = match.groups()
            if each:
                return _subfield_text(expansion, code) if expansion is not None else ""
            return _source_text(record, source_tag, code)

        expanded_template = _PLACEHOLDER.sub(substitute, template)
        built = parse_field(expanded_template)
        if mode == "replace":
            if not built.is_control_field() and not any(
                item.value for item in built.subfields
            ):
                raise TextFormError("replace result has no non-empty subfields")
            built_fields.append(built)
            built_fields.extend(
                parse_field(expanded_template) for _ in replace_targets[1:]
            )
        elif built.is_control_field() or any(item.value for item in built.subfields):
            built_fields.append(built)

    if mode == "replace":
        replacements = iter(built_fields)
        record.fields = [
            next(replacements) if field.tag == tag else field
            for field in record.fields
        ]
    elif built_fields:
        insert_fields(record, built_fields)
