import json
from pathlib import Path

import jsonschema
from pymarc import MARCReader

from open_marc_tasks import load_task, records_match, run_task


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_ROOT = REPOSITORY_ROOT / "conformance"


def read_records(path):
    with path.open("rb") as stream:
        return list(MARCReader(stream, to_unicode=True, utf8_handling="strict"))


def test_all_conformance_cases_match_marc_edit_outputs():
    cases = sorted(path for path in CONFORMANCE_ROOT.glob("*/*") if path.is_dir())
    assert cases, "no conformance cases found"
    schema = json.loads((REPOSITORY_ROOT / "spec" / "task.schema.json").read_text(encoding="utf-8"))
    required_files = {"task.json", "input.mrc", "expected.mrc", "marcedit-task.txt"}

    for case in cases:
        present_files = {path.name for path in case.iterdir() if path.is_file()}
        assert required_files <= present_files, "incomplete conformance case: {}".format(case)
        task_path = case / "task.json"
        task_document = json.loads(task_path.read_text(encoding="utf-8"))
        jsonschema.validate(task_document, schema)
        task = load_task(task_path)
        input_records = read_records(case / "input.mrc")
        expected_records = read_records(case / "expected.mrc")
        actual_records = list(run_task(task, input_records))

        assert len(actual_records) == len(expected_records), "record count differs: {}".format(case)
        assert all(records_match(actual, expected) for actual, expected in zip(actual_records, expected_records)), case
