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
from open_marc_tasks.marcedit_import import called_task_name, import_marcedit
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


def _task_sources(source_path):
    if source_path.suffix.lower() == ".task":
        with zipfile.ZipFile(source_path) as task_zip:
            return [
                (entry.filename, Path(entry.filename).stem, task_zip.read(entry).decode("utf-8"))
                for entry in task_zip.infolist()
                if not entry.is_dir()
                and Path(entry.filename).suffix.lower() == ".txt"
            ]
    return [(source_path.name, source_path.stem, source_path.read_text(encoding="utf-8"))]


def _collect_tasks(sources, task_directory):
    tasks = []
    tasks_by_name = {}
    for source_path, is_library in sources:
        result = import_marcedit(source_path)
        source_entries = _task_sources(source_path)
        for imported_task in result.tasks:
            matches = [entry for entry in source_entries if entry[1] == imported_task.name]
            if not matches:
                continue
            entry_name, _, text = matches[0]
            failures = [item for item in result.not_translated if item.source == entry_name]
            display_name = (
                "{}:{}".format(source_path, entry_name)
                if source_path.suffix.lower() == ".task"
                else str(source_path)
            )
            task = {
                "imported": imported_task,
                "name": imported_task.name,
                "text": text,
                "failures": failures,
                "display_name": display_name,
            }
            if not is_library:
                tasks.append(task)
            tasks_by_name.setdefault(imported_task.name, []).append(task)

    task_directory.mkdir()
    for name, matches in tasks_by_name.items():
        if all(task["text"] == matches[0]["text"] for task in matches[1:]):
            (task_directory / "{}.json".format(name)).write_text(
                json.dumps(matches[0]["imported"].document, ensure_ascii=False),
                encoding="utf-8",
            )
    return tasks, tasks_by_name


def _inline_task(task, tasks_by_name, stack=()):
    name = task["name"]
    if name in stack:
        return None, "TASK_LIST call cycle: {}".format(" -> ".join(stack + (name,)))

    if task["failures"]:
        failure = task["failures"][0]
        return None, "called task {} is not fully translated: {}:{} {}".format(
            name + ".json", failure.source, failure.line_number, failure.reason
        )

    lines = []
    for line in task["text"].splitlines():
        if line.startswith("TASK_LIST\t"):
            called_name = called_task_name(line)
            if called_name is None:
                return None, "malformed TASK_LIST line in {}".format(name + ".json")
            called_name = called_name[:-5]
            matches = tasks_by_name.get(called_name, [])
            if not matches:
                return None, "called task {} was not found".format(called_name + ".json")
            if any(task["text"] != matches[0]["text"] for task in matches[1:]):
                return None, "called task {} is ambiguous".format(called_name + ".json")
            called_text, reason = _inline_task(
                matches[0], tasks_by_name, stack + (name,)
            )
            if reason:
                return None, reason
            lines.extend(called_text.splitlines())
        else:
            lines.append(line)
    ending = "\n" if task["text"].endswith(("\n", "\r")) else ""
    return "\n".join(lines) + ending, None


def _has_empty_option_9(source_path):
    return any(
        len(columns) == 5
        and columns[0] == "SUBFIELD_REMOVE"
        and columns[3] == ""
        and columns[4] == "9|0"
        for columns in (
            line.split("\t")
            for line in source_path.read_text(encoding="utf-8").splitlines()
        )
    )


def _measure_task(task, tasks_by_name, task_directory, records_path, work_dir, number):
    display_name = task["display_name"]
    imported_task = task["imported"]
    failures = task["failures"]
    if failures:
        failure = failures[0]
        print(
            "{}: not translated ({}:{} {})".format(
                display_name, failure.source, failure.line_number, failure.reason
            )
        )
        return False

    inline_text, reason = _inline_task(task, tasks_by_name)
    if reason:
        print("{}: not translated ({})".format(display_name, reason))
        return False

    task_path = task_directory / "{}.json".format(imported_task.name)
    task_path.write_text(
        json.dumps(imported_task.document, ensure_ascii=False), encoding="utf-8"
    )
    task_source = work_dir / "reference-{}.txt".format(number)
    task_source.write_text(inline_text, encoding="utf-8")
    library_output = work_dir / "library-{}.mrc".format(number)
    reference_output = work_dir / "marcedit-{}.mrc".format(number)
    loaded_task = load_task(task_path)
    records = _read_records(records_path)
    _write_records(library_output, run_task(loaded_task, records))
    run_marcedit(task_source, records_path, reference_output, MARCEDIT_DIR)

    library_records = _read_records(library_output)
    reference_records = _read_records(reference_output)
    matches = len(library_records) == len(reference_records) and all(
        records_match(actual, expected)
        for actual, expected in zip(library_records, reference_records)
    )
    if matches:
        label = "match"
    elif _has_empty_option_9(task_source):
        label = "differs (deliberate: SUBFIELD_REMOVE option 9)"
    else:
        label = "differs"

    print("{}: {}".format(display_name, label))
    return matches


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure imported task agreement with MarcEdit.")
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument(
        "--library",
        action="append",
        type=Path,
        metavar="DIR",
        help="folder of .txt or .task files available to calls, but not measured (repeatable)",
    )
    parser.add_argument("folders", nargs="+", type=Path)
    arguments = parser.parse_args(argv)

    sources = [
        (source, False)
        for source in sorted(
            source
            for folder in arguments.folders
            for source in folder.rglob("*")
            if source.is_file() and source.suffix.lower() in (".txt", ".task")
        )
    ]
    sources.extend(
        (source, True)
        for source in sorted(
            source
            for folder in arguments.library or []
            for source in folder.rglob("*")
            if source.is_file() and source.suffix.lower() in (".txt", ".task")
        )
    )
    matched = 0
    with tempfile.TemporaryDirectory(
        prefix="omt-measure-", dir=str(REPOSITORY_ROOT)
    ) as temporary_directory:
        work_dir = Path(temporary_directory)
        task_directory = work_dir / "tasks"
        tasks, tasks_by_name = _collect_tasks(sources, task_directory)
        for number, task in enumerate(tasks):
            if _measure_task(
                task,
                tasks_by_name,
                task_directory,
                arguments.records,
                work_dir,
                number,
            ):
                matched += 1

    print("{} of {} task files match MarcEdit".format(matched, len(tasks)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
