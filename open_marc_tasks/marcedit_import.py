import re
import zipfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

from .commands.build_field import validate as validate_build_field
from .commands.call_task import validate as validate_call_task
from .commands.copy_field import validate as validate_copy_field
from .commands.delete_field import validate as validate_delete_field
from .commands.edit_field import validate as validate_edit_field
from .commands.edit_subfield import validate as validate_edit_subfield
from .commands.replace_text import validate as validate_replace_text
from .commands.remove_subfield import validate as validate_remove_subfield
from .commands.sort_fields import validate as validate_sort_fields
from .commands.set_indicators import validate as validate_set_indicators
from .commands.gather_subfields import validate as validate_gather_subfields
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
_SUBFIELD_REMOVE_ESCAPES = {"dollar": "$", "lcub": "{", "rcub": "}"}
_COPY_MATCH_ESCAPES = {"dollar", "lcub", "rcub"}
_GATHER_LOOP_FIND = re.compile(
    r"\(=([0-9]{3})\)\(\[\^\\r\\n\]\*\?\)"
    r"\(\\\$([a-z0-9])\[\^\\r\\n\]\*\)"
    r"\(\.\*\)\(=([0-9]{3})\[\^\\n\\r\]\*\)\(\.\*\)/m"
)


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
    opening = len(condition) - len(condition.lstrip("/"))
    closing = len(condition) - len(condition.rstrip("/"))
    if not 1 <= opening <= 3 or opening != closing:
        raise ValueError("unsupported ADD condition")
    return _leader_condition(
        condition[opening:-closing], "unsupported ADD condition"
    )


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

    text = text.lstrip(" ")
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


def called_task_name(line: str) -> Optional[str]:
    columns = line.split("\t")
    if (
        len(columns) != 3
        or columns[0] != "TASK_LIST"
        or not columns[2].endswith(".txt")
    ):
        return None
    name = columns[1].rsplit("|", 1)[-1]
    return "{}.-{}.json".format(name, Path(columns[2]).stem)


def _translate(line: str) -> Tuple[Optional[Dict[str, object]], str]:
    columns = line.split("\t")
    command = columns[0]

    if command == "TASK_LIST":
        task_name = called_task_name(line)
        if task_name is None:
            if len(columns) != 3:
                return None, "malformed TASK_LIST line"
            return None, "TASK_LIST file must end in .txt"
        step = {"command": "call_task", "task": task_name}
        try:
            validate_call_task(step, 1)
        except TaskError as error:
            return None, str(error)
        return step, ""

    if command == "COPY":
        if len(columns) != 8:
            return None, "malformed COPY line"
        _, from_tag, to_tag, move, match, column6, column7, column8 = columns
        if column6 or column7 != "false" or column8:
            return None, "unsupported COPY settings"
        if move not in ("false", "true"):
            return None, "unsupported COPY move setting"
        if from_tag.startswith("00") and to_tag.startswith("00"):
            return None, "COPY between control fields is not supported yet"
        if from_tag.startswith("00") and match:
            return None, "filtered COPY from control fields is not supported yet"

        mnemonics = _MNEMONIC.findall(match)
        if any(mnemonic not in _COPY_MATCH_ESCAPES for mnemonic in mnemonics):
            return None, "unsupported COPY match mnemonic"

        step = {"command": "copy_field", "from_tag": from_tag, "to_tag": to_tag}
        if move == "true":
            step["move"] = True
        if match:
            step["if_contains"] = match
        try:
            validate_copy_field(step, 1)
        except TaskError as error:
            return None, str(error)
        return step, ""

    if command == "SORTBY":
        if len(columns) < 2:
            return None, "malformed SORTBY line"
        target = columns[1]
        if target not in ("ALL", "0XX"):
            return None, "unsupported SORTBY target"
        if target == "0XX" and len(columns) == 2:
            step = {"command": "sort_fields", "scope": "0xx"}
        elif (
            len(columns) == 4
            and columns[2] in ("True", "False")
            and columns[3] in ("True", "False")
        ):
            step = {"command": "sort_fields", "scope": "all" if target == "ALL" else "0xx"}
        else:
            return None, "unsupported SORTBY settings"
        try:
            validate_sort_fields(step, 1)
        except TaskError as error:
            return None, str(error)
        return step, ""

    if command == "buildnewfield":
        if len(columns) != 6:
            return None, "malformed buildnewfield line"
        _, field, f1, f2, f3, f4 = columns
        if f1 != "False":
            return None, "buildnewfield f1 is not supported"

        flags = (f2, f3, f4)
        if flags == ("False", "False", "True"):
            mode = "add"
        elif flags == ("False", "True", "False"):
            mode = "add_if_missing"
        elif flags == ("True", "False", "False"):
            mode = "replace"
        else:
            return None, "unsupported buildnewfield flags"

        step = {"command": "build_field", "field": field, "mode": mode}
        try:
            validate_build_field(step, 1)
        except TaskError as error:
            return None, str(error)
        return step, ""

    if command == "DELETE":
        if len(columns) == 10 and columns[-1] == "":
            columns = columns[:-1]
        if len(columns) != 9:
            return None, "malformed DELETE line"
        tag = columns[1].replace("x", "X")
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
        if len(columns) == 7 and columns[5:] == ["100", ""]:
            columns = columns[:5]
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

    if command == "INDICATOR":
        if len(columns) != 5:
            return None, "malformed INDICATOR line"
        _, tag, find, condition, value = columns
        if len(tag) != 3 or not tag.isascii() or not tag.isdigit():
            return None, "invalid INDICATOR tag"
        if condition:
            return None, "INDICATOR condition is not supported"
        if len(value) not in (1, 2):
            return None, "INDICATOR value must be one or two characters"
        if len(find) > 2 or len(find) > len(value):
            return None, "INDICATOR find must be no longer than value and at most two characters"

        step = {"command": "set_indicators", "tag": tag, "value": value.replace("\\", " ")}
        if find:
            step["if_starts_with"] = find.replace("\\", " ")
        try:
            validate_set_indicators(step, 1)
        except TaskError as error:
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
        step = {"command": "edit_subfield", "tag": tag, "code": code}
        if flags == "0|2" and find:
            step.update({"action": "replace_regex", "find": find, "replace": replacement})
            try:
                validate_edit_subfield(step, 1)
            except TaskError as error:
                return None, str(error)
            return step, ""
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

    if command == "SUBFIELD_REMOVE":
        if len(columns) != 5:
            return None, "malformed SUBFIELD_REMOVE line"
        _, tag, code, value, flags = columns
        if len(tag) != 3 or not tag.isascii() or not tag.isdigit():
            return None, "invalid SUBFIELD_REMOVE tag"
        if tag.startswith("00"):
            return None, "SUBFIELD_REMOVE tag must be a data-field tag"
        if len(code) != 1 or code not in "abcdefghijklmnopqrstuvwxyz0123456789":
            return None, "invalid SUBFIELD_REMOVE subfield code"
        if flags.startswith("9|") and value:
            return None, "option 9 with a value is not supported"
        if flags not in ("107|0", "0|0", "9|0", "0|2"):
            return None, "unsupported SUBFIELD_REMOVE settings"

        step = {"command": "remove_subfield", "tag": tag, "code": code}
        if flags == "0|2":
            if not value:
                return None, "SUBFIELD_REMOVE regex needs a non-empty pattern"
            step["remove_regex"] = value
            try:
                validate_remove_subfield(step, 1)
            except TaskError as error:
                return None, str(error)
            return step, ""

        mnemonics = _MNEMONIC.findall(value)
        if any(mnemonic and mnemonic not in _SUBFIELD_REMOVE_ESCAPES for mnemonic in mnemonics):
            return None, "unsupported SUBFIELD_REMOVE character mnemonic"
        value = _MNEMONIC.sub(
            lambda match: _SUBFIELD_REMOVE_ESCAPES.get(match.group(1), match.group(0)),
            value,
        )

        if flags == "9|0":
            step["duplicates"] = True
        elif value:
            step["if_contains" if flags == "107|0" else "remove_text"] = value
        try:
            validate_remove_subfield(step, 1)
        except TaskError as error:
            return None, str(error)
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

    if command == "EDITFIELD":
        if len(columns) != 6:
            return None, "malformed EDITFIELD line"
        _, tag, find, option, replacement, final_column = columns
        if len(tag) != 3 or not tag.isascii() or not tag.isdigit():
            return None, "invalid EDITFIELD tag"
        if not find:
            return None, "EDITFIELD find must be non-empty"
        if option not in ("0", "2") or final_column:
            return None, "unsupported EDITFIELD settings"

        step = {
            "command": "edit_field",
            "tag": tag,
            "find": find,
            "replace": replacement,
        }
        if option == "2":
            step["regex"] = True
        try:
            validate_edit_field(step, 1)
        except TaskError as error:
            return None, str(error)
        return step, ""

    return None, "unknown MarcEdit command"


def _translate_gather_loop(
    lines: List[str], start: int, end: int
) -> Tuple[Optional[Dict[str, object]], str]:
    if lines[start] != "#STARTLOOP:r=0" or end != start + 2:
        return None, "unsupported MarcEdit loop"

    columns = lines[start + 1].split("\t")
    if (
        len(columns) != 7
        or columns[0] != "REPLACE"
        or columns[2] != r"=999$2$3$4$5$3$6"
        or columns[3:] != ["2", "", "0", "False"]
    ):
        return None, "unsupported MarcEdit loop"

    match = _GATHER_LOOP_FIND.fullmatch(columns[1])
    if match is None:
        return None, "unsupported MarcEdit loop"

    step = {
        "command": "gather_subfields",
        "from_tag": match.group(1),
        "code": match.group(2),
        "to_tag": match.group(3),
        "remove_source": True,
    }
    try:
        validate_gather_subfields(step, 1)
    except TaskError as error:
        return None, str(error)

    has_delete_999 = any(
        _translate(line)[0] == {"command": "delete_field", "tag": "999"}
        for line in lines[end + 1 :]
    )
    if not has_delete_999:
        return None, "gather_subfields loop requires a later DELETE 999"
    return step, ""


def _import_text(text: str, source: str, name: str) -> Tuple[ImportedTask, List[NotTranslated]]:
    description = ""
    description_seen = False
    steps = []
    not_translated = []
    lines = text.splitlines()

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("#STARTLOOP"):
            end = next(
                (position for position in range(index + 1, len(lines)) if lines[position] == "#ENDLOOP"),
                len(lines),
            )
            has_end = end < len(lines)
            if has_end:
                step, reason = _translate_gather_loop(lines, index, end)
            else:
                step, reason = None, "unsupported MarcEdit loop"

            if step is not None:
                steps.append(step)
            else:
                for position in range(index + 1, end):
                    if lines[position].strip() and not lines[position].startswith("#"):
                        not_translated.append(
                            NotTranslated(source, position + 1, lines[position], reason)
                        )
            index = end + 1 if has_end else len(lines)
            continue

        if not line.strip() or line.startswith("#"):
            if line.startswith("#DESCRIPTION#") and not description_seen:
                description = line[len("#DESCRIPTION#") :].lstrip("\t ")
                description_seen = True
            index += 1
            continue

        step, reason = _translate(line)
        if step is None:
            not_translated.append(NotTranslated(source, index + 1, line, reason))
        else:
            steps.append(step)
        index += 1

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
