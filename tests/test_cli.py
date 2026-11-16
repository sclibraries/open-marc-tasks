import json
from pathlib import Path
import subprocess

import pytest
from pymarc import Field, MARCReader, Record, Subfield

from open_marc_tasks import records_match


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WILDCARD_CASE = REPOSITORY_ROOT / "conformance" / "delete_field" / "wildcard"


def synthetic_record():
    record = Record(force_utf8=True)
    record.add_field(Field(tag="001", data="synthetic-record"))
    record.add_field(
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", "Synthetic title")],
        )
    )
    return record.as_marc()


def read_records(path):
    with path.open("rb") as source:
        return list(MARCReader(source, to_unicode=True, utf8_handling="strict"))


def run_omt(task_path, input_path, output_path):
    return subprocess.run(
        ["omt", "run", str(task_path), str(input_path), str(output_path)],
        capture_output=True,
        text=True,
    )


def write_task(path, steps=None):
    path.write_text(
        json.dumps(
            {
                "format_version": "0.1",
                "name": "Synthetic CLI task",
                "description": "Exercises safe CLI file handling.",
                "steps": steps if steps is not None else [{"command": "delete_field", "tag": "999"}],
            }
        ),
        encoding="utf-8",
    )


def test_run_writes_matching_conformance_output_and_preserves_utf8_bytes(tmp_path):
    task_path = WILDCARD_CASE / "task.json"
    input_path = WILDCARD_CASE / "input.mrc"
    expected_path = WILDCARD_CASE / "expected.mrc"
    output_path = tmp_path / "output.mrc"

    result = run_omt(task_path, input_path, output_path)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    utf8_value = "Café".encode("utf-8")
    assert input_path.read_bytes().count(utf8_value) == 1
    assert output_path.read_bytes().count(utf8_value) == 1
    actual_records = read_records(output_path)
    expected_records = read_records(expected_path)
    assert len(actual_records) == len(expected_records)
    assert all(
        records_match(actual, expected)
        for actual, expected in zip(actual_records, expected_records)
    )


@pytest.mark.parametrize(
    "case,record_number,message",
    [
        ("invalid task", None, "task"),
        ("empty input", None, "empty"),
        ("truncated second record", 2, "record 2"),
        ("MARC-8 leader", 1, "convert to UTF-8 first"),
        ("invalid UTF-8", 1, "record 1"),
        ("input is output", None, "same file"),
        ("all fields deleted", 1, "record 1"),
    ],
)
def test_run_errors_once_and_leaves_output_unchanged(tmp_path, case, record_number, message):
    task_path = tmp_path / "task.json"
    input_path = tmp_path / "input.mrc"
    output_path = tmp_path / "output.mrc"
    record = synthetic_record()
    write_task(task_path)
    input_path.write_bytes(record)

    if case == "invalid task":
        task_path.write_text("{", encoding="utf-8")
    elif case == "empty input":
        input_path.write_bytes(b"")
    elif case == "truncated second record":
        input_path.write_bytes(record + record[:-1])
    elif case == "MARC-8 leader":
        input_path.write_bytes(record[:9] + b" " + record[10:])
    elif case == "invalid UTF-8":
        input_path.write_bytes(record.replace(b"Synthetic title", b"\xffynthetic title"))
    elif case == "input is output":
        output_path = input_path
    elif case == "all fields deleted":
        write_task(
            task_path,
            steps=[
                {"command": "delete_field", "tag": "001"},
                {"command": "delete_field", "tag": "245"},
            ],
        )

    if output_path != input_path:
        output_path.write_bytes(b"existing output must survive")
    original_output = output_path.read_bytes()

    result = run_omt(task_path, input_path, output_path)

    assert result.returncode == 1
    assert result.stdout == ""
    error_lines = result.stderr.splitlines()
    assert len(error_lines) == 1
    assert error_lines[0].startswith("omt:")
    assert message in error_lines[0]
    if record_number is not None:
        assert "record {}".format(record_number) in error_lines[0]
    assert output_path.read_bytes() == original_output
