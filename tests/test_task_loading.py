import json
from pathlib import Path

import jsonschema
import pytest
from pymarc import Field, Record, Subfield

from open_marc_tasks import TaskError, load_task, run_task


VALID_STEP = {"command": "delete_field", "tag": "999"}
INVALID_DOCUMENTS = [
    ("wrong version", {"format_version": "9.9", "name": "x", "description": "x", "steps": [VALID_STEP]}, None),
    ("missing command", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"tag": "999"}]}, "step 2"),
    ("unknown command", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "unknown"}]}, "step 2"),
    ("missing tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field"}]}, "step 2"),
    ("short tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "9X"}]}, "step 2"),
    ("trailing newline tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "999\n"}]}, "step 2"),
    ("lowercase tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "9xx"}]}, "step 2"),
    ("nondigit tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "abc"}]}, "step 2"),
    ("unknown setting", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "999", "case_sensitive": True}]}, "step 2"),
    ("step is not an object", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, "delete 999"]}, "step 2"),
    ("add missing subfields", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0"}]}, "step 2"),
    ("add bad indicator length", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": "  ", "ind2": "0", "subfields": [["a", "Topic"]]}]}, "step 2"),
    ("add bad subfield code", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0", "subfields": [["A", "Topic"]]}]}, "step 2"),
    ("add unknown if_tag_exists", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0", "subfields": [["a", "Topic"]], "if_tag_exists": "unknown"}]}, "step 2"),
    ("add Leader position 24", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0", "subfields": [["a", "Topic"]], "when": [{"leader": 24, "in": ["a"]}]}]}, "step 2"),
    ("add empty condition in", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0", "subfields": [["a", "Topic"]], "when": [{"leader": 7, "in": []}]}]}, "step 2"),
]


def task_document(steps=None, format_version="0.1"):
    return {
        "format_version": format_version,
        "name": "Synthetic delete-field task",
        "description": "Removes a synthetic local field.",
        "steps": steps if steps is not None else [{"command": "delete_field", "tag": "999"}],
    }


@pytest.fixture
def task_schema():
    schema_path = Path(__file__).resolve().parents[1] / "spec" / "task.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name,document,step_number", INVALID_DOCUMENTS)
def test_invalid_tasks_are_rejected_by_loader_and_schema(tmp_path, task_schema, name, document, step_number):
    task_path = tmp_path / (name.replace(" ", "-") + ".json")
    task_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(TaskError) as error:
        load_task(task_path)
    if step_number:
        assert step_number in str(error.value)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document, task_schema)


@pytest.mark.parametrize("contents", ['{"format_version":', None])
def test_unreadable_or_malformed_task_raises_task_error(tmp_path, contents):
    task_path = tmp_path / "broken.json"
    if contents is not None:
        task_path.write_text(contents, encoding="utf-8")

    with pytest.raises(TaskError):
        load_task(task_path)


def test_run_task_consumes_generator_once_and_mutates_records_in_order(tmp_path):
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task_document()), encoding="utf-8")
    task = load_task(task_path)
    records = []
    for identifier in ("one", "two", "three"):
        record = Record()
        record.add_field(Field(tag="001", data=identifier))
        record.add_field(Field(tag="999", indicators=[" ", " "], subfields=[Subfield("a", "remove")]))
        record.add_field(Field(tag="245", indicators=["1", "0"], subfields=[Subfield("a", "Café archive")]))
        records.append(record)

    result = list(run_task(task, (record for record in records)))

    assert result == records
    assert [record["001"].data for record in result] == ["one", "two", "three"]
    assert all(record.get_fields("999") == [] for record in records)
    assert all(record["245"]["a"] == "Café archive" for record in records)
