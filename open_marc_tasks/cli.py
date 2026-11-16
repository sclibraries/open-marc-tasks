import argparse
import os
import sys
import tempfile
from pathlib import Path

from pymarc import MARCReader

from .task import load_task, run_task


class CLIError(Exception):
    """Raised when command arguments or records are invalid."""


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CLIError(message)


def _run(task_path, input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)
    if input_path.resolve() == output_path.resolve():
        raise CLIError("input and output resolve to the same file")

    task = load_task(task_path)
    temporary_path = None
    try:
        with input_path.open("rb") as source:
            if not source.read(1):
                raise CLIError("input file is empty")
            source.seek(0)
            reader = MARCReader(
                source,
                to_unicode=True,
                utf8_handling="strict",
            )
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(output_path.parent), delete=False
            ) as destination:
                temporary_path = Path(destination.name)
                record_number = 0
                while True:
                    try:
                        record = next(reader)
                    except StopIteration:
                        break
                    except UnicodeError as error:
                        raise CLIError(
                            "record {} contains invalid UTF-8".format(record_number + 1)
                        ) from error

                    record_number += 1
                    if record is None:
                        raise CLIError("could not read record {}".format(record_number))
                    if record.leader[9] != "a":
                        raise CLIError(
                            "record {} is not UTF-8; convert to UTF-8 first".format(record_number)
                        )
                    for result in run_task(task, (record,)):
                        if not result.fields:
                            raise CLIError(
                                "record {} has no fields left after the task".format(record_number)
                            )
                        destination.write(result.as_marc())

        os.replace(str(temporary_path), str(output_path))
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def main(argv=None):
    parser = ArgumentParser(prog="omt")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("task")
    run_parser.add_argument("input")
    run_parser.add_argument("output")

    try:
        arguments = parser.parse_args(argv)
        _run(arguments.task, arguments.input, arguments.output)
        return 0
    except Exception as error:
        message = " ".join(str(error).splitlines()).strip()
        print("omt: {}".format(message or error.__class__.__name__), file=sys.stderr)
        return 1
