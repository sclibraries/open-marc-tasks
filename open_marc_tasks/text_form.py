from pymarc import Field, Subfield


class TextFormError(ValueError):
    """Raised when replacement text is not a valid field text form."""


_VALUE_ESCAPES = {
    "{dollar}": "$",
    "{lcub}": "{",
    "{rcub}": "}",
}
_CONTROL_ESCAPES = dict(_VALUE_ESCAPES, **{"{bsol}": "\\"})


def _escape(value, blanks=False, backslash=False):
    escaped = []
    for char in value:
        if char == "$":
            escaped.append("{dollar}")
        elif char == "{":
            escaped.append("{lcub}")
        elif char == "}":
            escaped.append("{rcub}")
        elif char == "\\" and backslash:
            escaped.append("{bsol}")
        elif char == " " and blanks:
            escaped.append("\\")
        else:
            escaped.append(char)
    return "".join(escaped)


def _decode(value, escapes, blanks=False):
    decoded = []
    index = 0
    while index < len(value):
        if blanks and value[index] == "\\":
            decoded.append(" ")
            index += 1
            continue
        for spelling, character in escapes.items():
            if value.startswith(spelling, index):
                decoded.append(character)
                index += len(spelling)
                break
        else:
            decoded.append(value[index])
            index += 1
    return "".join(decoded)


def render_field(field):
    """Return the one-line text form of a pymarc field."""
    prefix = "={}".format(field.tag) + "  "
    if field.is_control_field():
        return prefix + _escape(field.data, blanks=True, backslash=True)

    indicators = "".join("\\" if value == " " else value for value in field.indicators)
    subfields = "".join(
        "${}{}".format(subfield.code, _escape(subfield.value))
        for subfield in field.subfields
    )
    return prefix + indicators + subfields


def transform_record_text(record, transform):
    """Transform the Leader and field text lines in place."""
    leader_prefix = "=LDR  "
    leader_line = leader_prefix + str(record.leader)
    transformed_leader = transform(leader_line)
    if transformed_leader != leader_line:
        if not transformed_leader.startswith(leader_prefix) or len(transformed_leader) != 30:
            raise TextFormError(
                "Leader text must start with '=LDR  ' and contain 24 characters"
            )
        record.leader[0:24] = transformed_leader[len(leader_prefix) :]

    for index, field in enumerate(record.fields):
        field_line = render_field(field)
        transformed = transform(field_line)
        if transformed != field_line:
            record.fields[index] = parse_field(transformed)


def parse_field(text):
    """Parse one field text form into a pymarc field."""
    if (
        not isinstance(text, str)
        or len(text) < 6
        or text[0] != "="
        or text[4:6] != "  "
    ):
        raise TextFormError("field text must start with '=' and a three-digit tag")

    tag = text[1:4]
    if len(tag) != 3 or not tag.isascii() or not tag.isdigit():
        raise TextFormError("field text tag must be three ASCII digits")

    body = text[6:]
    if tag in {"00{}".format(number) for number in range(1, 10)}:
        return Field(tag=tag, data=_decode(body, _CONTROL_ESCAPES, blanks=True))

    if len(body) < 2:
        raise TextFormError("data field text must include two indicators")
    indicators = [" " if char == "\\" else char for char in body[:2]]
    remainder = body[2:]
    subfields = []
    while remainder:
        if len(remainder) < 2 or remainder[0] != "$":
            raise TextFormError("data field text must contain subfields after its indicators")
        code = remainder[1]
        if not code.isascii() or code not in "abcdefghijklmnopqrstuvwxyz0123456789":
            raise TextFormError("data field text has an invalid subfield code")
        next_subfield = remainder.find("$", 2)
        if next_subfield == -1:
            raw_value = remainder[2:]
            remainder = ""
        else:
            raw_value = remainder[2:next_subfield]
            remainder = remainder[next_subfield:]
        subfields.append(Subfield(code, _decode(raw_value, _VALUE_ESCAPES)))

    return Field(tag=tag, indicators=indicators, subfields=subfields)
