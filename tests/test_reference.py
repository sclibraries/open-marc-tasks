import shutil
from pathlib import Path

import pytest
from pymarc import MARCReader

from open_marc_tasks import records_match


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_ROOT = REPOSITORY_ROOT / "conformance"
MARCEDIT_DIR = REPOSITORY_ROOT / "reference" / "marcedit"


def read_records(path):
    with path.open("rb") as source:
        return list(MARCReader(source, to_unicode=True, utf8_handling="strict"))


def test_expected_outputs_match_fresh_marcedit_runs(tmp_path):
    if not MARCEDIT_DIR.is_dir():
        pytest.skip("reference/marcedit not found")
    if shutil.which("docker") is None:
        pytest.skip("docker not found")

    from tools.marcedit_reference import run_marcedit

    cases = sorted(path for path in CONFORMANCE_ROOT.glob("*/*") if path.is_dir())
    assert cases, "no conformance cases found"

    for case in cases:
        actual_path = tmp_path / "{}.mrc".format(case.name)
        run_marcedit(
            case / "marcedit-task.txt",
            case / "input.mrc",
            actual_path,
            MARCEDIT_DIR,
        )
        actual_records = read_records(actual_path)
        expected_records = read_records(case / "expected.mrc")

        assert len(actual_records) == len(expected_records), "record count differs: {}".format(case)
        assert all(
            records_match(actual, expected)
            for actual, expected in zip(actual_records, expected_records)
        ), case
