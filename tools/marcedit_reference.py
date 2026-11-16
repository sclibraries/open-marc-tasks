import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pymarc import MARCReader

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from open_marc_tasks.task import blank_backslash_indicators


IMAGE = "mcr.microsoft.com/dotnet/runtime-deps:8.0"


def run_marcedit(tasks_file: Path, input_mrc: Path, output_mrc: Path, marcedit_dir: Path) -> None:
    marcedit_dir = marcedit_dir.resolve()
    with tempfile.TemporaryDirectory(
        prefix="marcedit-reference-", dir=str(REPOSITORY_ROOT)
    ) as temporary_directory:
        work_dir = Path(temporary_directory)
        task_copy = work_dir / "task.txt"
        input_copy = work_dir / "input.mrc"
        generated_output = work_dir / "output.mrc"
        shutil.copyfile(tasks_file, task_copy)
        shutil.copyfile(input_mrc, input_copy)

        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--platform",
                "linux/amd64",
                "--network",
                "none",
                "-e",
                "HOME=/tmp",
                "-e",
                "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1",
                "-v",
                "{}:/marcedit:ro".format(marcedit_dir),
                "-v",
                "{}:/work".format(work_dir),
                IMAGE,
                "/marcedit/cmarcedit",
                "-s",
                "/work/input.mrc",
                "-d",
                "/work/output.mrc",
                "-task",
                "/work/task.txt",
                "-silent",
            ],
            check=True,
        )

        if generated_output.stat().st_size == 0:
            with input_copy.open("rb") as source, output_mrc.open("wb") as destination:
                reader = MARCReader(source, to_unicode=True, utf8_handling="strict")
                for record in reader:
                    blank_backslash_indicators(record)
                    destination.write(record.as_marc())
        else:
            shutil.copyfile(generated_output, output_mrc)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Run MarcEdit for conformance references.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    regenerate = subparsers.add_parser("regenerate", help="regenerate expected MARC files")
    regenerate.add_argument("case_dirs", type=Path, nargs="+")
    args = parser.parse_args(argv)

    marcedit_dir = REPOSITORY_ROOT / "reference" / "marcedit"
    if not marcedit_dir.is_dir():
        parser.error("MarcEdit reference directory not found: {}".format(marcedit_dir))

    for case_dir in args.case_dirs:
        run_marcedit(
            case_dir / "marcedit-task.txt",
            case_dir / "input.mrc",
            case_dir / "expected.mrc",
            marcedit_dir,
        )


if __name__ == "__main__":
    main()
