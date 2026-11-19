import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping, Optional

from pymarc import MARCReader

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from open_marc_tasks.task import blank_backslash_indicators, normalize_typography


IMAGE = "mcr.microsoft.com/dotnet/runtime-deps:8.0"


def run_marcedit(
    tasks_file: Path,
    input_mrc: Path,
    output_mrc: Path,
    marcedit_dir: Path,
    macros: Optional[Mapping[str, str]] = None,
    configs: Optional[Path] = None,
) -> None:
    marcedit_dir = marcedit_dir.resolve()
    with tempfile.TemporaryDirectory(
        prefix="marcedit-reference-", dir=str(REPOSITORY_ROOT)
    ) as temporary_directory:
        work_dir = Path(temporary_directory)
        task_copy = work_dir / "task.txt"
        input_copy = work_dir / "input.mrc"
        generated_output = work_dir / "output.mrc"
        configured_home = macros is not None or configs is not None
        if configured_home:
            user_data = work_dir / "home" / ".config" / "marcedit75"
            macro_dir = user_data / "macros"
            config_dir = user_data / "configs"
            macro_dir.mkdir(parents=True)
            config_dir.mkdir()
            for name, text in (macros or {}).items():
                (macro_dir / name).write_text(text, encoding="utf-8")
            if configs is not None:
                shutil.copytree(configs, config_dir, dirs_exist_ok=True)
        shutil.copyfile(tasks_file, task_copy)
        shutil.copyfile(input_mrc, input_copy)

        command = [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "--network",
            "none",
            "-e",
            "HOME=/work/home" if configured_home else "HOME=/tmp",
            "-e",
            "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1",
            "-v",
            "{}:/marcedit:ro".format(marcedit_dir),
            "-v",
            "{}:/work".format(work_dir),
        ]
        if configured_home:
            command.extend(["-w", "/work/home/.config/marcedit75/macros"])
        command.extend(
            [
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
        )
        subprocess.run(command, check=True)

        if generated_output.stat().st_size == 0:
            with input_copy.open("rb") as source, output_mrc.open("wb") as destination:
                reader = MARCReader(source, to_unicode=True, utf8_handling="strict")
                for record in reader:
                    blank_backslash_indicators(record)
                    normalize_typography(record)
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
        macros_dir = case_dir / "marcedit-macros"
        macros = (
            {
                path.name: path.read_text(encoding="utf-8")
                for path in macros_dir.iterdir()
                if path.is_file()
            }
            if macros_dir.is_dir()
            else None
        )
        configs_dir = case_dir / "marcedit-configs"
        run_marcedit(
            case_dir / "marcedit-task.txt",
            case_dir / "input.mrc",
            case_dir / "expected.mrc",
            marcedit_dir,
            macros=macros,
            configs=configs_dir if configs_dir.is_dir() else None,
        )


if __name__ == "__main__":
    main()
