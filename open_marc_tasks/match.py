from pymarc import Record


def _field_value(field):
    if field.is_control_field():
        return field.tag, field.data
    return (
        field.tag,
        tuple(field.indicators),
        tuple((subfield.code, subfield.value) for subfield in field.subfields),
    )


def records_match(a: Record, b: Record) -> bool:
    """Return whether two records have equal content under the format's rule."""
    left_fields = [_field_value(field) for field in a.fields if field.tag != "005"]
    right_fields = [_field_value(field) for field in b.fields if field.tag != "005"]
    leader_positions = tuple(range(5, 10)) + tuple(range(17, 20))
    left_leader = tuple(a.leader[index] for index in leader_positions)
    right_leader = tuple(b.leader[index] for index in leader_positions)
    return left_fields == right_fields and left_leader == right_leader


