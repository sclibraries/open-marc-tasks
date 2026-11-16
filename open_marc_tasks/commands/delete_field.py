from pymarc import Record


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
