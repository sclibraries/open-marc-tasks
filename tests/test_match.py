import copy

import pytest
from pymarc import Field, Record, Subfield

from open_marc_tasks import records_match


def record_snapshot(record):
    fields = []
    for field in record.fields:
        if field.is_control_field():
            fields.append((field.tag, field.data))
        else:
            fields.append(
                (
                    field.tag,
                    tuple(field.indicators),
                    tuple((subfield.code, subfield.value) for subfield in field.subfields),
                )
            )
    return record.leader, tuple(fields)


def sample_record():
    record = Record()
    record.add_field(Field(tag="001", data="synthetic-1"))
    record.add_field(Field(tag="005", data="20260101000000.0"))
    record.add_field(
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", "Example archive"), Subfield("b", "A title")],
        )
    )
    record.add_field(
        Field(tag="650", indicators=[" ", "0"], subfields=[Subfield("a", "Synthetic records")])
    )
    return record


def mutate_record(record, difference):
    if difference == "field order":
        record.fields[2], record.fields[3] = record.fields[3], record.fields[2]
    elif difference == "indicator":
        record.fields[2] = Field(tag="245", indicators=["0", "0"], subfields=record.fields[2].subfields)
    elif difference == "subfield code":
        record.fields[2] = Field(
            tag="245", indicators=["1", "0"], subfields=[Subfield("c", "Example archive"), Subfield("b", "A title")]
        )
    elif difference == "subfield whitespace":
        record.fields[2] = Field(
            tag="245", indicators=["1", "0"], subfields=[Subfield("a", "Example  archive"), Subfield("b", "A title")]
        )
    elif difference == "control data":
        record.fields[0].data = "synthetic-2"
    elif difference == "leader 06":
        record.leader = record.leader[:6] + "b" + record.leader[7:]
    elif difference == "005":
        record.fields[1].data = "20261231235959.9"
    elif difference == "leader 00-04":
        record.leader = "99999" + record.leader[5:]


@pytest.mark.parametrize(
    "difference,expected",
    [
        ("field order", False),
        ("indicator", False),
        ("subfield code", False),
        ("subfield whitespace", False),
        ("control data", False),
        ("leader 06", False),
        ("005", True),
        ("leader 00-04", True),
    ],
)
def test_records_match_uses_the_documented_comparison(difference, expected):
    left = sample_record()
    right = copy.deepcopy(left)
    mutate_record(right, difference)
    left_before = record_snapshot(left)
    right_before = record_snapshot(right)

    assert records_match(left, right) is expected
    assert record_snapshot(left) == left_before
    assert record_snapshot(right) == right_before
