import re
import zipfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple


class ImportedTask(NamedTuple):
    name: str
    document: dict


class NotTranslated(NamedTuple):
    source: str
    line_number: int
    text: str
    reason: str


class ImportResult(NamedTuple):
    tasks: List[ImportedTask]
    not_translated: List[NotTranslated]


_DELETE_FLAGS = ["False"] * 5
_CONDITION_BRACKETS = re.compile(
    r"/=LDR\.\{([0-9]+)\}\[([A-Za-z]+(?:,[A-Za-z]+)*)\]"
    r"(?:\[([A-Za-z]+(?:,[A-Za-z]+)*)\])?\.\+/"
)
_CONDITION_SINGLE = re.compile(r"/=LDR\.\{([0-9]+)\}([A-Za-z])\.\+/")
_MNEMONIC = re.compile(r"\{([^{}]*)\}")
_SUBFIELD = re.compile(r"\$([a-z0-9])")


def _condition_values(values: str) -> List[str]:
    result = values.split(",")
    if len(result) == 1 and len(result[0]) > 1:
        result = list(result[0])
    if any(len(value) != 1 for value in result):
        raise ValueError("unsupported Leader condition values")
    return result


def _condition(condition: str) -> List[Dict[str, object]]:
    match = _CONDITION_BRACKETS.fullmatch(condition)
    if match:
        offset = int(match.group(1))
        if not 2 <= offset <= 25:
            raise ValueError("Leader condition position is out of range")
        first_values = _condition_values(match.group(2))
        conditions = [{"leader": offset - 2, "in": first_values}]
        second_group = match.group(3)
        if second_group is not None:
            if offset > 24:
                raise ValueError("Leader condition position is out of range")
            second_values = _condition_values(second_group)
            conditions.append({"leader": offset - 1, "in": second_values})
        return conditions

    match = _CONDITION_SINGLE.fullmatch(condition)
    if match:
        offset = int(match.group(1))
        if not 2 <= offset <= 25:
            raise ValueError("Leader condition position is out of range")
        return [{"leader": offset - 2, "in": [match.group(2)]}]

    raise ValueError("unsupported ADD condition")


def _field(tag: str, text: str) -> Dict[str, object]:
    mnemonics = _MNEMONIC.findall(text)
    if any(mnemonic != "dollar" for mnemonic in mnemonics):
        raise ValueError("unsupported field mnemonic")

    if tag.startswith("00"):
        return {
            "command": "add_field",
            "tag": tag,
            "data": text.replace("{dollar}", "$"),
        }

    if len(text) < 2:
        raise ValueError("ADD field text needs two indicators")
    indicators = [" " if char == "\\" else char for char in text[:2]]
    body = text[2:]
    parts = _SUBFIELD.split(body)
    if len(parts) < 3 or parts[0] != "":
        raise ValueError("ADD field text needs subfields")

    subfields = []
    for index in range(1, len(parts), 2):
        value = parts[index + 1]
        if "$" in value:
            raise ValueError("unsupported dollar in field text")
        subfields.append([parts[index], value.replace("{dollar}", "$")])

    return {
        "command": "add_field",
        "tag": tag,
        "ind1": indicators[0],
        "ind2": indicators[1],
        "subfields": subfields,
    }


def _translate(line: str) -> Tuple[Optional[Dict[str, object]], str]:
    columns = line.split("\t")
    command = columns[0]

    if command == "DELETE":
        if len(columns) != 9:
            return None, "malformed DELETE line"
        if columns[2] != "":
            return None, "DELETE match values are not supported"
        if columns[3] != "0" or columns[4:] != _DELETE_FLAGS:
            return None, "non-default DELETE flags are not supported"
        tag = columns[1]
        if len(tag) != 3 or any(char not in "0123456789X" for char in tag):
            return None, "invalid DELETE tag"
        return {"command": "delete_field", "tag": tag}, ""

    if command == "ADD":
        if len(columns) != 5:
            return None, "malformed ADD line"
        _, tag, field_text, option, condition_text = columns
        if len(tag) != 3 or not tag.isascii() or not tag.isdigit():
            return None, "invalid ADD tag"
        policies = {"100": "add", "101": "skip", "108": "skip_if_identical"}
        if option not in policies and option != "106":
            return None, "unknown ADD option"
        if option != "106" and condition_text:
            return None, "ADD condition is not supported for this option"

        try:
            step = _field(tag, field_text)
            step["if_tag_exists"] = policies.get(option, "add")
            if option == "106":
                if not condition_text:
                    raise ValueError("ADD option 106 needs a Leader condition")
                step["when"] = _condition(condition_text)
        except ValueError as error:
            return None, str(error)
        return step, ""

    return None, "unknown MarcEdit command"


def _import_text(text: str, source: str, name: str) -> Tuple[ImportedTask, List[NotTranslated]]:
    description = ""
    description_seen = False
    steps = []
    not_translated = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.startswith("#"):
            if line.startswith("#DESCRIPTION#") and not description_seen:
                description = line[len("#DESCRIPTION#") :].lstrip("\t ")
                description_seen = True
            continue

        step, reason = _translate(line)
        if step is None:
            not_translated.append(NotTranslated(source, line_number, line, reason))
        else:
            steps.append(step)

    return (
        ImportedTask(
            name,
            {
                "format_version": "0.1",
                "name": name,
                "description": description,
                "steps": steps,
            },
        ),
        not_translated,
    )


def import_marcedit(path: Path) -> ImportResult:
    path = Path(path)
    tasks = []
    not_translated = []

    if path.suffix.lower() == ".task":
        with zipfile.ZipFile(path) as task_zip:
            for entry in task_zip.infolist():
                entry_path = Path(entry.filename)
                if entry.is_dir() or entry_path.suffix.lower() != ".txt":
                    continue
                source = entry.filename
                task, untranslated = _import_text(
                    task_zip.read(entry).decode("utf-8"), source, entry_path.stem
                )
                tasks.append(task)
                not_translated.extend(untranslated)
    else:
        task, untranslated = _import_text(
            path.read_text(encoding="utf-8"), path.name, path.stem
        )
        tasks.append(task)
        not_translated.extend(untranslated)

    return ImportResult(tasks, not_translated)
