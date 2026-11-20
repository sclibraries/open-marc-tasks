import json
from pathlib import Path
import subprocess

import pytest
from pymarc import Field, MARCReader, Record, Subfield

from open_marc_tasks import TaskError, load_task, records_match, run_task


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXACT_TAG_CASE = REPOSITORY_ROOT / "conformance" / "delete_field" / "exact-tag"


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
    task_path = EXACT_TAG_CASE / "task.json"
    input_path = EXACT_TAG_CASE / "input.mrc"
    expected_path = EXACT_TAG_CASE / "expected.mrc"
    output_path = tmp_path / "output.mrc"

    result = run_omt(task_path, input_path, output_path)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    utf8_value = "Café archive".encode("utf-8")
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
        ("empty build_field replacement", 2, "record 2 step 2"),
        ("invalid subfield regex result", 2, "record 2 step 2"),
        ("invalid edit_field result", 2, "record 2 step 2"),
        ("called task runtime error", 2, "record 2 step 2"),
        ("Leader rule invalid length", 2, "record 2 step 2"),
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
    elif case == "empty build_field replacement":
        write_task(
            task_path,
            steps=[
                {"command": "delete_field", "tag": "998"},
                {"command": "build_field", "field": "=950  \\\\$a{999$a}", "mode": "replace"},
            ],
        )
        first = Record(force_utf8=True)
        first.add_field(Field(tag="001", data="synthetic-1"))
        first.add_field(Field(tag="950", indicators=[" ", " "], subfields=[Subfield("a", "old-1")]))
        first.add_field(Field(tag="999", indicators=[" ", " "], subfields=[Subfield("a", "source")]))
        second = Record(force_utf8=True)
        second.add_field(Field(tag="001", data="synthetic-2"))
        second.add_field(Field(tag="950", indicators=[" ", " "], subfields=[Subfield("a", "old-2")]))
        input_path.write_bytes(first.as_marc() + second.as_marc())
    elif case == "invalid subfield regex result":
        write_task(
            task_path,
            steps=[
                {"command": "delete_field", "tag": "998"},
                {"command": "edit_subfield", "tag": "245", "code": "a", "action": "replace_regex", "find": "^a", "replace": "X"},
            ],
        )
        first = Record(force_utf8=True)
        first.add_field(Field(tag="001", data="synthetic-1"))
        second = Record(force_utf8=True)
        second.add_field(Field(tag="001", data="synthetic-2"))
        second.add_field(Field(tag="245", indicators=["1", "0"], subfields=[Subfield("a", "Synthetic title")]))
        input_path.write_bytes(first.as_marc() + second.as_marc())
    elif case == "invalid edit_field result":
        write_task(
            task_path,
            steps=[
                {"command": "delete_field", "tag": "998"},
                {"command": "edit_field", "tag": "245", "find": "$a", "replace": "$A"},
            ],
        )
        first = Record(force_utf8=True)
        first.add_field(Field(tag="001", data="synthetic-1"))
        second = Record(force_utf8=True)
        second.add_field(Field(tag="001", data="synthetic-2"))
        second.add_field(Field(tag="245", indicators=["1", "0"], subfields=[Subfield("a", "Synthetic title")]))
        input_path.write_bytes(first.as_marc() + second.as_marc())
    elif case == "called task runtime error":
        write_task(
            task_path,
            steps=[
                {"command": "delete_field", "tag": "998"},
                {"command": "call_task", "task": "child.json"},
            ],
        )
        (tmp_path / "child.json").write_text(
            json.dumps(
                {
                    "format_version": "0.1",
                    "name": "Synthetic child task",
                    "description": "Exercises errors in called tasks.",
                    "steps": [
                        {"command": "edit_field", "tag": "245", "find": "$a", "replace": "$A"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        first = Record(force_utf8=True)
        first.add_field(Field(tag="001", data="synthetic-1"))
        second = Record(force_utf8=True)
        second.add_field(Field(tag="001", data="synthetic-2"))
        second.add_field(Field(tag="245", indicators=["1", "0"], subfields=[Subfield("a", "Synthetic title")]))
        input_path.write_bytes(first.as_marc() + second.as_marc())
    elif case == "Leader rule invalid length":
        write_task(
            task_path,
            steps=[
                {"command": "delete_field", "tag": "999"},
                {
                    "command": "apply_rules",
                    "rules": [["=LDR", "^(=LDR  .....)[b]", "$1"]],
                },
            ],
        )
        first = Record(force_utf8=True)
        first.add_field(Field(tag="001", data="synthetic-1"))
        first.leader = str(first.leader)[:5] + "a" + str(first.leader)[6:]
        second = Record(force_utf8=True)
        second.add_field(Field(tag="001", data="synthetic-2"))
        second.leader = str(second.leader)[:5] + "b" + str(second.leader)[6:]
        input_path.write_bytes(first.as_marc() + second.as_marc())

    if output_path != input_path and case != "empty build_field replacement":
        output_path.write_bytes(b"existing output must survive")
    original_output = output_path.read_bytes() if output_path.exists() else None

    if case in ("empty build_field replacement", "invalid subfield regex result", "invalid edit_field result", "called task runtime error", "Leader rule invalid length"):
        with input_path.open("rb") as source:
            input_records = list(MARCReader(source, to_unicode=True, utf8_handling="strict"))
        with pytest.raises(TaskError, match="record 2 step 2"):
            list(run_task(load_task(task_path), input_records))

    result = run_omt(task_path, input_path, output_path)

    assert result.returncode == 1
    assert result.stdout == ""
    error_lines = result.stderr.splitlines()
    assert len(error_lines) == 1
    assert error_lines[0].startswith("omt:")
    assert message in error_lines[0]
    if case == "called task runtime error":
        assert "child.json" in error_lines[0]
        assert "step 1" in error_lines[0]
    if record_number is not None:
        assert "record {}".format(record_number) in error_lines[0]
    if original_output is None:
        assert not output_path.exists()
    else:
        assert output_path.read_bytes() == original_output
