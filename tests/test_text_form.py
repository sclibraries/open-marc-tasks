import json
import subprocess

import pytest
from pymarc import Field, Record, Subfield

from open_marc_tasks import TaskError, load_task, run_task
from open_marc_tasks.text_form import parse_field, render_field


ROUND_TRIPS = [
    (
        "control blanks",
        Field(tag="001", data="A\\B C TOUCH"),
        Field(tag="001", data="A\\B C EDITED"),
    ),
    (
        "blank indicators",
        Field(
            tag="245",
            indicators=[" ", " "],
            subfields=[Subfield("a", "Synthetic title"), Subfield("z", "TOUCH")],
        ),
        Field(
            tag="245",
            indicators=[" ", " "],
            subfields=[Subfield("a", "Synthetic title"), Subfield("z", "EDITED")],
        ),
    ),
    (
        "literal dollar",
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", "Price $5"), Subfield("z", "TOUCH")],
        ),
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", "Price $5"), Subfield("z", "EDITED")],
        ),
    ),
    (
        "literal dollar escape text",
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", "Text {dollar}"), Subfield("z", "TOUCH")],
        ),
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", "Text {dollar}"), Subfield("z", "EDITED")],
        ),
    ),
    (
        "literal backslash",
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", r"Path\name"), Subfield("z", "TOUCH")],
        ),
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", r"Path\name"), Subfield("z", "EDITED")],
        ),
    ),
    (
        "unmatched braces",
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", "Open { and close }"), Subfield("z", "TOUCH")],
        ),
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", "Open { and close }"), Subfield("z", "EDITED")],
        ),
    ),
]


INVALID_RESULTS = [
    ("tag is not three digits", "=24  10$aSOURCE"),
    ("data field has no indicators", "=245  "),
    ("subfield code is invalid", "=245  10$!value"),
]


def field_contents(field):
    if field.is_control_field():
        return field.tag, field.data
    return field.tag, tuple(field.indicators), [
        (subfield.code, subfield.value) for subfield in field.subfields
    ]


@pytest.mark.parametrize("name,field,expected", ROUND_TRIPS)
def test_field_text_round_trip_preserves_other_content_when_another_part_changes(
    name, field, expected
):
    text = render_field(field)
    assert "TOUCH" in text

    result = parse_field(text.replace("TOUCH", "EDITED"))

    assert field_contents(result) == field_contents(expected), name


@pytest.mark.parametrize("name,replacement", INVALID_RESULTS)
def test_invalid_replacement_names_record_and_step_and_preserves_cli_output(
    tmp_path, name, replacement
):
    task_path = tmp_path / "task.json"
    task_path.write_text(
        json.dumps(
            {
                "format_version": "0.1",
                "name": "Synthetic invalid replacement",
                "description": "Rejects malformed field text without writing output.",
                "steps": [
                    {"command": "delete_field", "tag": "999"},
                    {
                        "command": "replace_text",
                        "find": "=245  10$aSOURCE",
                        "replace": replacement,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    records = []
    for value in ("OTHER", "SOURCE"):
        record = Record(force_utf8=True)
        record.add_field(Field(tag="001", data="synthetic-record"))
        record.add_field(
            Field(tag="245", indicators=["1", "0"], subfields=[Subfield("a", value)])
        )
        records.append(record)

    task = load_task(task_path)
    with pytest.raises(TaskError) as error:
        list(run_task(task, records))
    assert "record 2" in str(error.value)
    assert "step 2" in str(error.value)

    input_path = tmp_path / "input.mrc"
    input_path.write_bytes(b"".join(record.as_marc() for record in records))
    output_path = tmp_path / "output.mrc"
    output_path.write_bytes(b"existing output")

    result = subprocess.run(
        ["omt", "run", str(task_path), str(input_path), str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, name
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("omt:")
    assert "record 2" in lines[0]
    assert "step 2" in lines[0]
    assert output_path.read_bytes() == b"existing output"
