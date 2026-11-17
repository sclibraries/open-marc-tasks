import re
import zipfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

from .commands.delete_field import validate as validate_delete_field
from .commands.replace_text import validate as validate_replace_text
from .task import TaskError


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
    r"=LDR\.\{([0-9]+)\}\[([A-Za-z]+(?:,[A-Za-z]+)*)\]"
    r"(?:\[([A-Za-z]+(?:,[A-Za-z]+)*)\])?\.\+"
)
_CONDITION_SINGLE = re.compile(r"=LDR\.\{([0-9]+)\}([A-Za-z])\.\+")
_MNEMONIC = re.compile(r"\{([^{}]*)\}")
_REGEX_QUANTIFIER = re.compile(r"[0-9]+(?:,[0-9]*)?\Z")
_SUBFIELD = re.compile(r"\$([a-z0-9])")
_FIELD_TEXT_ESCAPES = {"dollar", "lcub", "rcub", "bsol"}


def _condition_values(values: str) -> List[str]:
    result = values.split(",")
    if len(result) == 1 and len(result[0]) > 1:
        result = list(result[0])
    if any(len(value) != 1 for value in result):
        raise ValueError("unsupported Leader condition values")
    return result


def _leader_condition(
    condition: str, unsupported_message: str
) -> List[Dict[str, object]]:
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

    raise ValueError(unsupported_message)


def _condition(condition: str) -> List[Dict[str, object]]:
    if len(condition) < 2 or not condition.startswith("/") or not condition.endswith("/"):
        raise ValueError("unsupported ADD condition")
    return _leader_condition(condition[1:-1], "unsupported ADD condition")


def _replace_condition(condition: str) -> List[Dict[str, object]]:
    return _leader_condition(condition, "unsupported REPLACE condition")


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
        tag = columns[1]
        if len(tag) != 3 or any(char not in "0123456789X" for char in tag):
            return None, "invalid DELETE tag"
        match = columns[2]
        flags = columns[4:]
        if not match:
            if columns[3] != "0" or flags != _DELETE_FLAGS:
                return None, "non-default DELETE flags are not supported"
            return {"command": "delete_field", "tag": tag}, ""
        if (
            columns[3] not in ("0", "2")
            or flags[0] != "False"
            or flags[1] not in ("False", "True")
            or flags[2:] != _DELETE_FLAGS[2:]
        ):
            return None, "unsupported DELETE settings"

        step = {"command": "delete_field", "tag": tag, "match": match}
        if columns[3] == "2":
            step["match_regex"] = True
        if flags[1] == "True":
            step["delete_nonmatches"] = True
        try:
            validate_delete_field(step, 1)
        except TaskError as error:
            return None, str(error)
        return step, ""

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

    if command == "SUBFIELD_EDIT":
        if len(columns) != 6:
            return None, "malformed SUBFIELD_EDIT line"
        _, tag, code, find, replacement, flags = columns
        if len(tag) != 3 or any(char not in "0123456789" for char in tag):
            return None, "invalid SUBFIELD_EDIT tag"
        if len(code) != 1 or code not in "abcdefghijklmnopqrstuvwxyz0123456789":
            return None, "invalid SUBFIELD_EDIT subfield code"
        if flags == "0|2":
            return None, "SUBFIELD_EDIT regular expressions are not supported yet"

        step = {"command": "edit_subfield", "tag": tag, "code": code}
        if flags == "102|0" and find == "" and replacement:
            step.update({"action": "add", "value": replacement})
        elif flags == "101|0" and find == "" and replacement:
            step.update({"action": "add_if_missing", "value": replacement})
        elif flags == "0|0" and find == "^e" and replacement:
            step.update({"action": "append", "value": replacement})
        elif flags == "0|0" and find == "^b" and replacement:
            step.update({"action": "prepend", "value": replacement})
        elif flags == "0|0" and find == "" and replacement == "":
            step["action"] = "clear"
        elif flags == "0|0" and find:
            step.update({"action": "replace", "find": find, "replace": replacement})
        elif flags == "0|1" and find and replacement:
            step.update({"action": "replace_first", "find": find, "replace": replacement})
        else:
            return None, "unsupported SUBFIELD_EDIT settings"
        return step, ""

    if command == "REPLACE":
        if len(columns) != 7:
            return None, "malformed REPLACE line"
        _, find, replacement, find_flags, condition, replace_flags, case_sensitive = columns
        if (
            find_flags not in ("0", "2")
            or replace_flags != ("2" if condition else "0")
            or case_sensitive != "False"
            or (find_flags == "0" and condition)
        ):
            return None, "unsupported REPLACE settings"
        if not find:
            return None, "REPLACE find must be non-empty"

        step = {"command": "replace_text", "find": find, "replace": replacement}
        if find_flags == "2":
            if condition:
                try:
                    step["when"] = _replace_condition(condition)
                except ValueError as error:
                    return None, str(error)

            mnemonics = _MNEMONIC.findall(find) + _MNEMONIC.findall(replacement)
            if any(
                mnemonic and not _REGEX_QUANTIFIER.fullmatch(mnemonic)
                for mnemonic in mnemonics
            ):
                return None, "unsupported REPLACE character mnemonic"

            step["regex"] = True
            try:
                validate_replace_text(step, 1)
            except TaskError as error:
                return None, str(error)
            return step, ""

        mnemonics = _MNEMONIC.findall(find + replacement)
        if any(mnemonic and mnemonic not in _FIELD_TEXT_ESCAPES for mnemonic in mnemonics):
            return None, "unsupported REPLACE character mnemonic"
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
                "normalize_typography": True,
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
