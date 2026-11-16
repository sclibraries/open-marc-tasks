import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from pymarc import MARCReader

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from open_marc_tasks import records_match, run_task
from open_marc_tasks.marcedit_import import import_marcedit
from open_marc_tasks.task import load_task
from tools.marcedit_reference import run_marcedit


MARCEDIT_DIR = REPOSITORY_ROOT / "reference" / "marcedit"


def _read_records(path):
    with path.open("rb") as source:
        return list(MARCReader(source, to_unicode=True, utf8_handling="strict"))


def _write_records(path, records):
    with path.open("wb") as destination:
        for record in records:
            destination.write(record.as_marc())


def _task_file(source_path, imported_task, temporary_dir):
    if source_path.suffix.lower() != ".task":
        return source_path

    with zipfile.ZipFile(source_path) as task_zip:
        entry = next(
            entry
            for entry in task_zip.infolist()
            if not entry.is_dir()
            and Path(entry.filename).suffix.lower() == ".txt"
            and Path(entry.filename).stem == imported_task.name
        )
        task_path = temporary_dir / "{}.txt".format(imported_task.name)
        task_path.write_bytes(task_zip.read(entry))
    return task_path


def _measure_task(display_name, source_path, imported_task, records_path, failures):
    if failures:
        print("{}: not translated ({} lines)".format(display_name, len(failures)))
        return False

    with tempfile.TemporaryDirectory(
        prefix="omt-measure-", dir=str(REPOSITORY_ROOT)
    ) as temporary_directory:
        work_dir = Path(temporary_directory)
        task_source = _task_file(source_path, imported_task, work_dir)
        task_path = work_dir / "task.json"
        task_path.write_text(
            json.dumps(imported_task.document, ensure_ascii=False), encoding="utf-8"
        )
        library_output = work_dir / "library.mrc"
        reference_output = work_dir / "marcedit.mrc"
        task = load_task(task_path)
        records = _read_records(records_path)
        _write_records(library_output, run_task(task, records))
        run_marcedit(task_source, records_path, reference_output, MARCEDIT_DIR)

        library_records = _read_records(library_output)
        reference_records = _read_records(reference_output)
        matches = len(library_records) == len(reference_records) and all(
            records_match(actual, expected)
            for actual, expected in zip(library_records, reference_records)
        )

    print("{}: {}".format(display_name, "match" if matches else "differs"))
    return matches


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure imported task agreement with MarcEdit.")
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("folders", nargs="+", type=Path)
    arguments = parser.parse_args(argv)

    sources = sorted(
        source
        for folder in arguments.folders
        for source in folder.rglob("*")
        if source.is_file() and source.suffix.lower() in (".txt", ".task")
    )
    matched = 0
    total = 0

    for source in sources:
        result = import_marcedit(source)
        if source.suffix.lower() == ".task":
            with zipfile.ZipFile(source) as task_zip:
                entry_names = [
                    entry.filename
                    for entry in task_zip.infolist()
                    if not entry.is_dir()
                    and Path(entry.filename).suffix.lower() == ".txt"
                ]
        else:
            entry_names = [source.name]

        for imported_task in result.tasks:
            entry_name = next(
                name for name in entry_names if Path(name).stem == imported_task.name
            )
            failures = [
                item for item in result.not_translated if item.source == entry_name
            ]
            display_name = (
                "{}:{}".format(source, entry_name)
                if source.suffix.lower() == ".task"
                else str(source)
            )
            total += 1
            if _measure_task(
                display_name,
                source,
                imported_task,
                arguments.records,
                failures,
            ):
                matched += 1

    print("{} of {} task files match MarcEdit".format(matched, total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
